"""add project_name and user_id to projects

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-06-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'projects',
        sa.Column('project_name', sa.String(length=255), nullable=False, server_default=''),
    )
    op.add_column(
        'projects',
        sa.Column('user_id', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_project_user_id', 'projects', ['user_id'], unique=False)
    op.alter_column('projects', 'project_name', server_default=None)


def downgrade() -> None:
    op.drop_index('ix_project_user_id', table_name='projects')
    op.drop_column('projects', 'user_id')
    op.drop_column('projects', 'project_name')
