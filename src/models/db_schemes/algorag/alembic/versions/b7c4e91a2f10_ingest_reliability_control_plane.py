"""Ingest reliability control plane tables (017)

Revision ID: b7c4e91a2f10
Revises: 115ff82e229f
Create Date: 2026-07-18 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7c4e91a2f10"
down_revision: Union[str, None] = "115ff82e229f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("correlation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("logical_document_id", sa.String(length=255), nullable=False),
        sa.Column("logical_document_version", sa.String(length=255), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False),
        sa.Column("workload_class", sa.String(length=32), nullable=False),
        sa.Column("progress_stage", sa.String(length=128), nullable=True),
        sa.Column("progress_percent", sa.Float(), nullable=True),
        sa.Column("progress_kind", sa.String(length=32), nullable=False),
        sa.Column("checkpoint_ref", sa.String(length=255), nullable=True),
        sa.Column("publish_completion_id", sa.UUID(), nullable=True),
        sa.Column("capacity_claim_id", sa.UUID(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("parse_outcome", sa.String(length=32), nullable=True),
        sa.Column("failure_class", sa.String(length=64), nullable=True),
        sa.Column("failure_ownership", sa.String(length=64), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("configuration_version", sa.String(length=64), nullable=False),
        sa.Column("operational_mode_at_admit", sa.String(length=64), nullable=False),
        sa.Column("job_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_ingest_jobs_correlation_id", "ingest_jobs", ["correlation_id"])
    op.create_index("ix_ingest_jobs_project_id", "ingest_jobs", ["project_id"])
    op.create_index("ix_ingest_jobs_lifecycle_state", "ingest_jobs", ["lifecycle_state"])
    op.create_index(
        "ix_ingest_jobs_logical_doc",
        "ingest_jobs",
        ["logical_document_id", "logical_document_version"],
    )

    op.create_table(
        "ingest_operational_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("correlation_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=128), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ix_ingest_operational_events_job_id", "ingest_operational_events", ["job_id"]
    )
    op.create_index(
        "ix_ingest_operational_events_correlation_id",
        "ingest_operational_events",
        ["correlation_id"],
    )

    op.create_table(
        "ingest_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("checkpoint_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("stage", sa.String(length=128), nullable=False),
        sa.Column("progress_token", sa.Text(), nullable=False),
        sa.Column("reclaimable", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkpoint_id"),
    )
    op.create_index("ix_ingest_checkpoints_job_id", "ingest_checkpoints", ["job_id"])

    op.create_table(
        "ingest_capacity_claims",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("claim_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("workload_class", sa.String(length=32), nullable=False),
        sa.Column("reserved_units", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id"),
    )
    op.create_index("ix_ingest_capacity_claims_job_id", "ingest_capacity_claims", ["job_id"])

    op.create_table(
        "logical_document_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("logical_document_id", sa.String(length=255), nullable=False),
        sa.Column("version_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fully_committed", sa.Boolean(), nullable=False),
        sa.Column("quality_warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("superseded_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "logical_document_id",
            "version_id",
            name="uq_logical_document_version",
        ),
    )
    op.create_index(
        "ix_logical_doc_active",
        "logical_document_versions",
        ["project_id", "logical_document_id", "status"],
    )

    op.create_table(
        "publish_completions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("publish_completion_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("logical_document_id", sa.String(length=255), nullable=False),
        sa.Column("version_id", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("previous_active_version", sa.String(length=255), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publish_completion_id"),
        sa.UniqueConstraint(
            "project_id",
            "logical_document_id",
            "version_id",
            name="uq_publish_completion_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("publish_completions")
    op.drop_index("ix_logical_doc_active", table_name="logical_document_versions")
    op.drop_table("logical_document_versions")
    op.drop_index("ix_ingest_capacity_claims_job_id", table_name="ingest_capacity_claims")
    op.drop_table("ingest_capacity_claims")
    op.drop_index("ix_ingest_checkpoints_job_id", table_name="ingest_checkpoints")
    op.drop_table("ingest_checkpoints")
    op.drop_index(
        "ix_ingest_operational_events_correlation_id",
        table_name="ingest_operational_events",
    )
    op.drop_index(
        "ix_ingest_operational_events_job_id", table_name="ingest_operational_events"
    )
    op.drop_table("ingest_operational_events")
    op.drop_index("ix_ingest_jobs_logical_doc", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_lifecycle_state", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_project_id", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_correlation_id", table_name="ingest_jobs")
    op.drop_table("ingest_jobs")
