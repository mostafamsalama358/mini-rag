"""Exactly-once atomic publish completion."""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_control_plane import (
    LogicalDocumentVersion,
    PublishCompletion,
)
from models.db_schemes.algorag.schemes.ingest_job import IngestJob
from services.ingest_reliability.gates import integrity_pre_publish_gate
from services.ingest_reliability.job_service import IngestJobService
from services.ingest_reliability.models import LifecycleState
from utils.metrics import INGEST_PUBLISH_TOTAL


async def publish_version(
    db_client: object,
    *,
    job_id: str | UUID,
    project_id: int,
    logical_document_id: str,
    version_id: str,
    has_searchable_units: bool,
    metadata_complete: bool,
    with_warnings: bool = False,
) -> PublishCompletion:
    gate = integrity_pre_publish_gate(
        has_searchable_units=has_searchable_units,
        metadata_complete=metadata_complete,
        version_consistent=True,
    )
    if not gate.passed:
        svc = await IngestJobService.create_instance(db_client)
        await svc.transition(
            job_id,
            LifecycleState.FAILED,
            cause=gate.reason,
            stage="publishing",
        )
        INGEST_PUBLISH_TOTAL.labels(result="integrity_failed").inc()
        raise RuntimeError(f"integrity_gate_failed:{gate.reason}")

    previous_active: Optional[str] = None
    completion = PublishCompletion(
        publish_completion_id=uuid4(),
        project_id=project_id,
        logical_document_id=logical_document_id,
        version_id=version_id,
        job_id=UUID(str(job_id)),
        previous_active_version=None,
    )

    try:
        async with db_client() as session:
            async with session.begin():
                active_result = await session.execute(
                    select(LogicalDocumentVersion).where(
                        LogicalDocumentVersion.project_id == project_id,
                        LogicalDocumentVersion.logical_document_id == logical_document_id,
                        LogicalDocumentVersion.status == "active",
                    )
                )
                active = active_result.scalar_one_or_none()
                if active is not None:
                    previous_active = active.version_id
                    active.status = "superseded"
                    active.superseded_by = version_id
                    active.fully_committed = True

                ver_result = await session.execute(
                    select(LogicalDocumentVersion).where(
                        LogicalDocumentVersion.project_id == project_id,
                        LogicalDocumentVersion.logical_document_id == logical_document_id,
                        LogicalDocumentVersion.version_id == version_id,
                    )
                )
                version_row = ver_result.scalar_one_or_none()
                if version_row is None:
                    version_row = LogicalDocumentVersion(
                        project_id=project_id,
                        logical_document_id=logical_document_id,
                        version_id=version_id,
                        status="active",
                        fully_committed=True,
                    )
                    session.add(version_row)
                else:
                    version_row.status = "active"
                    version_row.fully_committed = True

                completion.previous_active_version = previous_active
                session.add(completion)

                job_result = await session.execute(
                    select(IngestJob).where(IngestJob.job_id == UUID(str(job_id)))
                )
                job = job_result.scalar_one_or_none()
                if job is not None:
                    job.publish_completion_id = completion.publish_completion_id
            await session.commit()
            await session.refresh(completion)
    except IntegrityError:
        # Exactly-once: duplicate publish for same version is a no-op.
        INGEST_PUBLISH_TOTAL.labels(result="exactly_once_noop").inc()
        async with db_client() as session:
            result = await session.execute(
                select(PublishCompletion).where(
                    PublishCompletion.project_id == project_id,
                    PublishCompletion.logical_document_id == logical_document_id,
                    PublishCompletion.version_id == version_id,
                )
            )
            existing = result.scalar_one()
        return existing

    svc = await IngestJobService.create_instance(db_client)
    terminal = (
        LifecycleState.COMPLETED_WITH_WARNINGS
        if with_warnings
        else LifecycleState.COMPLETED
    )
    await svc.transition(job_id, terminal, cause="publish_complete", stage="publishing")
    INGEST_PUBLISH_TOTAL.labels(result="activated").inc()
    return completion
