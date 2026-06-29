"""add chat_messages table

Revision ID: b7c8d9e0f1a2
Revises: a1c2d3e4f5b6
Create Date: 2026-06-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a1c2d3e4f5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_messages',
        sa.Column('message_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_uuid', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id']),
        sa.PrimaryKeyConstraint('message_id'),
        sa.UniqueConstraint('message_uuid'),
    )
    op.create_index('ix_chat_message_session_id', 'chat_messages', ['session_id'], unique=False)
    op.create_index('ix_chat_message_project_id', 'chat_messages', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chat_message_project_id', table_name='chat_messages')
    op.drop_index('ix_chat_message_session_id', table_name='chat_messages')
    op.drop_table('chat_messages')
