"""Durable IngestJob control-plane row (spec 017)."""

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

from .algorag_base import SQLAlchemyBase


class IngestJob(SQLAlchemyBase):
    __tablename__ = "ingest_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    project_id = Column(Integer, nullable=False)
    logical_document_id = Column(String(255), nullable=False)
    logical_document_version = Column(String(255), nullable=False)

    lifecycle_state = Column(String(64), nullable=False, default="Accepted")
    workload_class = Column(String(32), nullable=False, default="small")

    progress_stage = Column(String(128), nullable=True)
    progress_percent = Column(Float, nullable=True)
    progress_kind = Column(String(32), nullable=False, default="progressing")

    checkpoint_ref = Column(String(255), nullable=True)
    publish_completion_id = Column(UUID(as_uuid=True), nullable=True)
    capacity_claim_id = Column(UUID(as_uuid=True), nullable=True)
    celery_task_id = Column(String(255), nullable=True)

    parse_outcome = Column(String(32), nullable=True)
    failure_class = Column(String(64), nullable=True)
    failure_ownership = Column(String(64), nullable=True)
    failure_reason = Column(Text, nullable=True)

    configuration_version = Column(String(64), nullable=False, default="1.0.0")
    operational_mode_at_admit = Column(String(64), nullable=False, default="normal")
    job_metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    terminal_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ingest_jobs_project_id", "project_id"),
        Index("ix_ingest_jobs_lifecycle_state", "lifecycle_state"),
        Index(
            "ix_ingest_jobs_logical_doc",
            "logical_document_id",
            "logical_document_version",
        ),
    )
