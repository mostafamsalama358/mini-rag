"""Cancel / timeout control with capacity reclamation."""

from __future__ import annotations

from services.ingest_reliability.job_service import IngestJobService
from services.ingest_reliability.models import FailureOwnership, LifecycleState
from services.ingest_reliability.reclamation import reclaim_job_resources


async def cancel_job(
    db_client: object,
    job_id: str,
    *,
    cause: str = "operator_cancel",
) -> None:
    svc = await IngestJobService.create_instance(db_client)
    await svc.transition(
        job_id,
        LifecycleState.CANCELLED,
        cause=cause,
        stage="cancellation",
        extra={"ownership": FailureOwnership.OPERATOR_ACTION.value},
    )
    await reclaim_job_resources(db_client, job_id)


async def timeout_job(
    db_client: object,
    job_id: str,
    *,
    cause: str = "job_timeout",
) -> None:
    svc = await IngestJobService.create_instance(db_client)
    await svc.transition(
        job_id,
        LifecycleState.TIMED_OUT,
        cause=cause,
        stage="timeout",
        extra={"ownership": FailureOwnership.PLATFORM.value},
    )
    await reclaim_job_resources(db_client, job_id)
