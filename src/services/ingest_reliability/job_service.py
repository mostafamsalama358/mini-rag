"""IngestJob persistence service (spec 017)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_job import IngestJob
from models.db_schemes.algorag.schemes.ingest_control_plane import (
    IngestCapacityClaim,
    IngestOperationalEvent,
)
from services.ingest_reliability.history import build_history_event
from services.ingest_reliability.lifecycle import (
    IllegalLifecycleTransition,
    is_terminal,
    transition_job,
)
from services.ingest_reliability.models import (
    IngestJobCreate,
    LifecycleState,
    ProgressKind,
    WorkloadClass,
)


class IngestJobService:
    def __init__(self, db_client: object):
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object) -> "IngestJobService":
        return cls(db_client)

    async def create_job(self, payload: IngestJobCreate) -> IngestJob:
        job = IngestJob(
            job_id=uuid4(),
            correlation_id=UUID(payload.correlation_id)
            if payload.correlation_id
            else uuid4(),
            project_id=payload.project_id,
            logical_document_id=payload.logical_document_id,
            logical_document_version=payload.logical_document_version,
            lifecycle_state=LifecycleState.ACCEPTED.value,
            workload_class=payload.workload_class.value,
            progress_stage="admission",
            progress_kind=ProgressKind.PROGRESSING.value,
            configuration_version=payload.configuration_version,
            operational_mode_at_admit=payload.operational_mode_at_admit.value,
            celery_task_id=payload.celery_task_id,
            job_metadata=payload.metadata or {},
        )
        claim = IngestCapacityClaim(
            claim_id=uuid4(),
            job_id=job.job_id,
            workload_class=payload.workload_class.value,
            reserved_units=1,
            state="held",
        )
        job.capacity_claim_id = claim.claim_id
        event = build_history_event(
            job_id=str(job.job_id),
            correlation_id=str(job.correlation_id),
            event_type="lifecycle",
            detail={"state": LifecycleState.ACCEPTED.value, "cause": "admit"},
            stage="admission",
        )
        op_event = IngestOperationalEvent(
            event_id=UUID(event["event_id"]),
            job_id=job.job_id,
            correlation_id=job.correlation_id,
            event_type=event["event_type"],
            stage=event["stage"],
            detail=event["detail"],
        )

        async with self.db_client() as session:
            async with session.begin():
                session.add(job)
                session.add(claim)
                session.add(op_event)
            await session.commit()
            await session.refresh(job)
        return job

    async def get_by_job_id(self, job_id: str | UUID) -> Optional[IngestJob]:
        jid = UUID(str(job_id))
        async with self.db_client() as session:
            result = await session.execute(select(IngestJob).where(IngestJob.job_id == jid))
            return result.scalar_one_or_none()

    async def get_by_correlation_id(self, correlation_id: str | UUID) -> list[IngestJob]:
        cid = UUID(str(correlation_id))
        async with self.db_client() as session:
            result = await session.execute(
                select(IngestJob).where(IngestJob.correlation_id == cid)
            )
            return list(result.scalars().all())

    async def transition(
        self,
        job_id: str | UUID,
        new_state: LifecycleState,
        *,
        cause: str,
        stage: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> IngestJob:
        jid = UUID(str(job_id))
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(IngestJob).where(IngestJob.job_id == jid).with_for_update()
                )
                job = result.scalar_one()
                current = LifecycleState(job.lifecycle_state)
                transition_job(current=current, new_state=new_state, cause=cause)
                job.lifecycle_state = new_state.value
                if stage:
                    job.progress_stage = stage
                if is_terminal(new_state):
                    job.terminal_at = datetime.now(timezone.utc)
                    # Release capacity claim on terminal.
                    if job.capacity_claim_id:
                        claim_result = await session.execute(
                            select(IngestCapacityClaim).where(
                                IngestCapacityClaim.claim_id == job.capacity_claim_id
                            )
                        )
                        claim = claim_result.scalar_one_or_none()
                        if claim and claim.state == "held":
                            claim.state = "released"
                            claim.released_at = datetime.now(timezone.utc)
                detail = {"state": new_state.value, "cause": cause}
                if extra:
                    detail.update(extra)
                event = build_history_event(
                    job_id=str(job.job_id),
                    correlation_id=str(job.correlation_id),
                    event_type="lifecycle",
                    detail=detail,
                    stage=stage or job.progress_stage,
                )
                session.add(
                    IngestOperationalEvent(
                        event_id=UUID(event["event_id"]),
                        job_id=job.job_id,
                        correlation_id=job.correlation_id,
                        event_type=event["event_type"],
                        stage=event["stage"],
                        detail=event["detail"],
                    )
                )
            await session.commit()
            await session.refresh(job)
        return job

    async def update_progress(
        self,
        job_id: str | UUID,
        *,
        stage: str,
        kind: ProgressKind = ProgressKind.PROGRESSING,
        percent: Optional[float] = None,
    ) -> IngestJob:
        jid = UUID(str(job_id))
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(IngestJob).where(IngestJob.job_id == jid)
                )
                job = result.scalar_one()
                job.progress_stage = stage
                job.progress_kind = kind.value
                if percent is not None:
                    job.progress_percent = percent
            await session.commit()
            await session.refresh(job)
        return job

    async def attach_celery_task(
        self, job_id: str | UUID, celery_task_id: str
    ) -> IngestJob:
        jid = UUID(str(job_id))
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(IngestJob).where(IngestJob.job_id == jid)
                )
                job = result.scalar_one()
                job.celery_task_id = celery_task_id
            await session.commit()
            await session.refresh(job)
        return job


def classify_workload(size_bytes: int, large_threshold: int) -> WorkloadClass:
    if size_bytes >= large_threshold:
        return WorkloadClass.LARGE
    return WorkloadClass.SMALL


__all__ = ["IngestJobService", "classify_workload", "IllegalLifecycleTransition"]
