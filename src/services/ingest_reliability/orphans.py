"""Orphan detection and recovery ownership."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_control_plane import IngestCheckpoint
from models.db_schemes.algorag.schemes.ingest_job import IngestJob
from services.ingest_reliability.job_service import IngestJobService
from services.ingest_reliability.lifecycle import TERMINAL_STATES, is_terminal
from services.ingest_reliability.models import LifecycleState
from services.ingest_reliability.reclamation import reclaim_job_resources
from utils.metrics import INGEST_ORPHAN_RECOVERY_TOTAL


@dataclass
class OrphanOutcome:
    job_id: str
    outcome: str  # resumed | reclaimed | failed_explicit | operator_pending


async def detect_orphan_jobs(
    db_client: object, *, stale_minutes: int = 30
) -> list[IngestJob]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    async with db_client() as session:
        result = await session.execute(select(IngestJob))
        jobs = list(result.scalars().all())
    orphans: list[IngestJob] = []
    for job in jobs:
        try:
            state = LifecycleState(job.lifecycle_state)
        except ValueError:
            continue
        if is_terminal(state):
            continue
        updated = job.updated_at or job.created_at
        if updated is not None and updated.replace(tzinfo=timezone.utc) < cutoff:
            orphans.append(job)
    return orphans


async def recover_orphan_job(db_client: object, job: IngestJob) -> OrphanOutcome:
    """Reclaim by default when no resume token; else mark operator_pending."""
    jid = str(job.job_id)
    async with db_client() as session:
        cp_result = await session.execute(
            select(IngestCheckpoint)
            .where(IngestCheckpoint.job_id == job.job_id)
            .order_by(IngestCheckpoint.created_at.desc())
            .limit(1)
        )
        cp = cp_result.scalar_one_or_none()

    if cp is not None and cp.progress_token:
        INGEST_ORPHAN_RECOVERY_TOTAL.labels(outcome="operator_pending").inc()
        return OrphanOutcome(jid, "operator_pending")

    svc = await IngestJobService.create_instance(db_client)
    await svc.transition(
        job.job_id,
        LifecycleState.FAILED,
        cause="orphan_reclaimed",
        stage="recovery",
    )
    await reclaim_job_resources(db_client, jid)
    INGEST_ORPHAN_RECOVERY_TOTAL.labels(outcome="reclaimed").inc()
    return OrphanOutcome(jid, "reclaimed")


async def recover_stale_orphans(db_client: object) -> list[OrphanOutcome]:
    outcomes = []
    for job in await detect_orphan_jobs(db_client):
        outcomes.append(await recover_orphan_job(db_client, job))
    return outcomes
