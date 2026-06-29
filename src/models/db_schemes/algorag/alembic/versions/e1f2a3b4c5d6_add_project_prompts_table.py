"""add project prompts table

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-06-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_prompts',
        sa.Column('prompt_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('prompt_en', sa.Text(), nullable=True),
        sa.Column('prompt_ar', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('prompt_id')
    )
    op.create_index('ix_project_prompt_project_id', 'project_prompts', ['project_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_project_prompt_project_id', table_name='project_prompts')
    op.drop_table('project_prompts')
