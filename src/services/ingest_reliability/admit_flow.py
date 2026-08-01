"""HTTP admission helper for process endpoints (spec 017 T016)."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from helpers.config import Settings
from models.db_schemes.algorag.schemes.ingest_control_plane import IngestCapacityClaim
from services.ingest_reliability.admission import AdmissionController, AdmissionDecision
from services.ingest_reliability.capacity import CapacityLedger
from services.ingest_reliability.job_service import IngestJobService, classify_workload
from services.ingest_reliability.models import (
    AdmissionOutcome,
    IngestJobCreate,
    OperationalMode,
    WorkloadClass,
)

logger = logging.getLogger("uvicorn.error")

# Process-local ledger supplements DB counts for single-worker fairness.
_LOCAL_LEDGER = CapacityLedger()


async def count_held_claims(db_client: object) -> int:
    async with db_client() as session:
        result = await session.execute(
            select(func.count())
            .select_from(IngestCapacityClaim)
            .where(IngestCapacityClaim.state == "held")
        )
        return int(result.scalar_one() or 0)


def sync_ledger_from_held(held: int, settings: Settings) -> CapacityLedger:
    """Rebuild a simple ledger snapshot for decisioning (units ≈ held jobs)."""
    ledger = CapacityLedger(
        max_concurrent=settings.INGEST_MAX_CONCURRENT_JOBS,
        interactive_reserved=settings.INGEST_INTERACTIVE_RESERVED_SLOTS,
    )
    for i in range(held):
        ledger.hold(
            job_id=f"held-snapshot-{i}",
            workload_class=WorkloadClass.SMALL,
            units=1,
        )
    return ledger


async def admit_ingest_job(
    *,
    request: Any,
    project_id: int,
    file_id: Optional[str],
    asset_size_bytes: int,
    settings: Settings,
) -> tuple[Optional[Any], Optional[JSONResponse]]:
    """Return (job, error_response). error_response set on delay/reject."""
    from services.ingest_reliability.config_safety import validate_ingest_config
    from services.ingest_reliability.rollout import scalable_path_enabled_for_project

    if not settings.INGEST_RELIABILITY_ENABLED:
        return None, None
    if not scalable_path_enabled_for_project(project_id, settings):
        return None, None
    ok, reason = validate_ingest_config(settings)
    if not ok:
        return None, JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": "INGEST_CONFIG_INVALID", "reason": reason},
        )

    workload = classify_workload(asset_size_bytes, settings.INGEST_LARGE_DOCUMENT_BYTES)
    hard_max = settings.INGEST_HARD_MAX_BYTES
    if hard_max <= 0:
        hard_max = int(settings.FILE_MAX_SIZE) * 1024 * 1024
    if hard_max > 0 and asset_size_bytes > hard_max:
        return None, JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": "INGEST_HARD_SIZE_EXCEEDED",
                "reason": "hard_max_bytes",
                "max_bytes": hard_max,
            },
        )

    try:
        held = await count_held_claims(request.app.db_client)
    except Exception as exc:  # pragma: no cover - DB not migrated yet
        logger.warning("ingest admission claim count failed: %s", exc)
        held = _LOCAL_LEDGER.held_units()

    ledger = sync_ledger_from_held(held, settings)
    controller = AdmissionController(ledger, settings)
    decision: AdmissionDecision = controller.decide(workload)

    if decision.outcome == AdmissionOutcome.DELAY:
        return None, JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "signal": "INGEST_ADMISSION_DELAY",
                "reason": decision.reason,
                "outcome": decision.outcome.value,
            },
        )
    if decision.outcome == AdmissionOutcome.REJECT:
        return None, JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "signal": "INGEST_ADMISSION_REJECT",
                "reason": decision.reason,
                "outcome": decision.outcome.value,
            },
        )

    logical_id = file_id or f"project-{project_id}-upload"
    version_id = str(uuid4())
    try:
        mode = OperationalMode(settings.INGEST_OPERATIONAL_MODE.lower())
    except ValueError:
        mode = OperationalMode.NORMAL

    service = await IngestJobService.create_instance(request.app.db_client)
    try:
        job = await service.create_job(
            IngestJobCreate(
                project_id=project_id,
                logical_document_id=str(logical_id),
                logical_document_version=version_id,
                workload_class=workload,
                configuration_version=settings.INGEST_CONFIG_VERSION,
                operational_mode_at_admit=mode,
                metadata={"asset_size_bytes": asset_size_bytes},
            )
        )
        try:
            _LOCAL_LEDGER.hold(job_id=str(job.job_id), workload_class=workload, units=1)
        except RuntimeError:
            pass
        return job, None
    except Exception as exc:
        logger.exception("ingest job create failed: %s", exc)
        # Do not block legacy processing if control plane write fails.
        return None, None
