"""Supporting ingest control-plane tables (spec 017)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

from .algorag_base import SQLAlchemyBase


class IngestOperationalEvent(SQLAlchemyBase):
    __tablename__ = "ingest_operational_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    stage = Column(String(128), nullable=True)
    detail = Column(JSONB, nullable=False, default=dict)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IngestCheckpoint(SQLAlchemyBase):
    __tablename__ = "ingest_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    stage = Column(String(128), nullable=False)
    progress_token = Column(Text, nullable=False)
    reclaimable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IngestCapacityClaim(SQLAlchemyBase):
    __tablename__ = "ingest_capacity_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    workload_class = Column(String(32), nullable=False)
    reserved_units = Column(Integer, nullable=False, default=1)
    state = Column(String(16), nullable=False, default="held")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)


class LogicalDocumentVersion(SQLAlchemyBase):
    __tablename__ = "logical_document_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    logical_document_id = Column(String(255), nullable=False)
    version_id = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="preparing")
    fully_committed = Column(Boolean, nullable=False, default=False)
    quality_warnings = Column(JSONB, nullable=True)
    superseded_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "logical_document_id",
            "version_id",
            name="uq_logical_document_version",
        ),
        Index("ix_logical_doc_active", "project_id", "logical_document_id", "status"),
    )


class PublishCompletion(SQLAlchemyBase):
    __tablename__ = "publish_completions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    publish_completion_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    project_id = Column(Integer, nullable=False)
    logical_document_id = Column(String(255), nullable=False)
    version_id = Column(String(255), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    previous_active_version = Column(String(255), nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "logical_document_id",
            "version_id",
            name="uq_publish_completion_version",
        ),
    )
