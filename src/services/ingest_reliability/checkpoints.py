"""Checkpoint commit/load for resumable ingest."""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_control_plane import IngestCheckpoint
from models.db_schemes.algorag.schemes.ingest_job import IngestJob


async def commit_checkpoint(
    db_client: object,
    *,
    job_id: str | UUID,
    stage: str,
    progress_token: str,
    reclaimable: bool = True,
) -> IngestCheckpoint:
    jid = UUID(str(job_id))
    cp = IngestCheckpoint(
        checkpoint_id=uuid4(),
        job_id=jid,
        stage=stage,
        progress_token=progress_token,
        reclaimable=reclaimable,
    )
    async with db_client() as session:
        async with session.begin():
            session.add(cp)
            result = await session.execute(select(IngestJob).where(IngestJob.job_id == jid))
            job = result.scalar_one_or_none()
            if job is not None:
                job.checkpoint_ref = str(cp.checkpoint_id)
        await session.commit()
        await session.refresh(cp)
    return cp


async def latest_checkpoint(
    db_client: object, job_id: str | UUID
) -> Optional[IngestCheckpoint]:
    jid = UUID(str(job_id))
    async with db_client() as session:
        result = await session.execute(
            select(IngestCheckpoint)
            .where(IngestCheckpoint.job_id == jid)
            .order_by(IngestCheckpoint.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


def is_resume_eligible(
    *,
    checkpoint: Optional[IngestCheckpoint],
    cancelled: bool,
    poisoned: bool,
    within_retry_budget: bool,
) -> bool:
    if cancelled or poisoned or not within_retry_budget:
        return False
    return checkpoint is not None and bool(checkpoint.progress_token)
