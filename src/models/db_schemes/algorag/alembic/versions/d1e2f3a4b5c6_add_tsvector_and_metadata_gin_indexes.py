"""Add tsvector GIN index on chunks.chunk_text and metadata GIN index.

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-06-22

Changes
-------
* GIN index ``ix_chunk_text_tsvector`` on ``to_tsvector('simple', chunk_text)``
  — accelerates I1 (BM25 sparse retrieval) ``search_by_text()`` queries.
* GIN index ``ix_chunk_metadata_gin`` on ``chunk_metadata`` (JSONB)
  — accelerates I3 (page filter) and N2 (metadata pre-filter) queries.

Both indexes are created with ``IF NOT EXISTS`` so this migration is safe to
run against a DB that already has them (e.g. from SQLAlchemy model
``__table_args__``).  The ``downgrade()`` drops them idempotently.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # GIN index for tsvector full-text search (BM25 channel — I1).
    # Uses the 'simple' text-search config so it works for any language
    # (Arabic, English, etc.) without a language-specific dictionary.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunk_text_tsvector
        ON chunks
        USING GIN (to_tsvector('simple', chunk_text))
        """
    )

    # GIN index for JSONB containment queries (page filter I3, metadata N2).
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunk_metadata_gin
        ON chunks
        USING GIN (chunk_metadata)
        WHERE chunk_metadata IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunk_text_tsvector")
    op.execute("DROP INDEX IF EXISTS ix_chunk_metadata_gin")
