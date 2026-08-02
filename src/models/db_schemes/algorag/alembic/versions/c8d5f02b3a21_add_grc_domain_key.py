"""Add grc value to domain_key enum.

Revision ID: c8d5f02b3a21
Revises: b7c4e91a2f10
Create Date: 2026-08-01 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "c8d5f02b3a21"
down_revision: Union[str, None] = "b7c4e91a2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: ADD VALUE cannot run inside a transaction block on older
    # versions; use IF NOT EXISTS (PG 9.1+ for ADD VALUE; IF NOT EXISTS PG 9.3+/15).
    op.execute("ALTER TYPE domain_key ADD VALUE IF NOT EXISTS 'grc'")


def downgrade() -> None:
    # Native PostgreSQL enums cannot drop a single value safely without
    # recreating the type and rewriting dependent columns — leave as no-op.
    pass
