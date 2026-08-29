"""Add madrsty value to domain_key enum.

Revision ID: e9f1b3c4d5a6
Revises: c8d5f02b3a21
Create Date: 2026-08-23 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e9f1b3c4d5a6"
down_revision: Union[str, None] = "c8d5f02b3a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE domain_key ADD VALUE IF NOT EXISTS 'madrsty'")


def downgrade() -> None:
    pass
