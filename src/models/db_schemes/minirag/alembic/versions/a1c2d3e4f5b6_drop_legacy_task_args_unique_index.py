"""drop legacy celery task args unique index

Revision ID: a1c2d3e4f5b6
Revises: 243ca8b683b0
Create Date: 2026-06-15 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1c2d3e4f5b6'
down_revision: Union[str, None] = '243ca8b683b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ixz_task_name_args_hash')


def downgrade() -> None:
    op.create_index(
        'ixz_task_name_args_hash',
        'celery_task_executions',
        ['task_name', 'task_args_hash'],
        unique=True,
    )
