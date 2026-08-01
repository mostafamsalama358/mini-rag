"""Best-effort job progress updates from Celery tasks."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_job import IngestJob
from services.ingest_reliability.job_service import IngestJobService
from services.ingest_reliability.models import LifecycleState, ProgressKind

logger = logging.getLogger(__name__)


async def find_job_by_celery_task(
    db_client: object, celery_task_id: str
) -> Optional[IngestJob]:
    async with db_client() as session:
        result = await session.execute(
            select(IngestJob).where(IngestJob.celery_task_id == celery_task_id)
        )
        return result.scalar_one_or_none()


async def mark_stage(
    db_client: object,
    celery_task_id: str,
    *,
    state: Optional[LifecycleState] = None,
    stage: str,
    kind: ProgressKind = ProgressKind.PROGRESSING,
    percent: Optional[float] = None,
) -> None:
    try:
        job = await find_job_by_celery_task(db_client, celery_task_id)
        if job is None:
            return
        svc = await IngestJobService.create_instance(db_client)
        if state is not None:
            await svc.transition(
                job.job_id, state, cause="stage_progress", stage=stage
            )
        await svc.update_progress(
            job.job_id, stage=stage, kind=kind, percent=percent
        )
    except Exception as exc:
        logger.debug("ingest progress update skipped: %s", exc)
