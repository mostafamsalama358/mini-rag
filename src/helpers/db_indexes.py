"""Idempotent creation of indexes that are too important to leave to a
manual migration.

Each statement uses ``CREATE INDEX IF NOT EXISTS``, so this is safe to run on
every startup regardless of whether the index already exists. Keeping these
out of the ORM model definition avoids relying on ``metadata.create_all`` (this
project does not run it) and avoids requiring an Alembic migration for an
index-only change.
"""
import logging
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("uvicorn")

# (index_name, ddl) pairs.  Index names are stable so ``IF NOT EXISTS`` is
# reliable.  Each of these also has a matching Alembic migration in
# ``models/db_schemes/algorag/alembic/versions/`` — this helper merely
# ensures the index exists for deployments that have not yet run that
# migration.
_STARTUP_INDEXES = (
    (
        "ix_chunk_metadata_gin",
        (
            "CREATE INDEX IF NOT EXISTS ix_chunk_metadata_gin "
            "ON chunks USING gin (chunk_metadata) "
            "WHERE chunk_metadata IS NOT NULL"
        ),
    ),
    (
        "ix_chunk_text_tsvector",
        (
            "CREATE INDEX IF NOT EXISTS ix_chunk_text_tsvector "
            "ON chunks USING GIN (to_tsvector('simple', chunk_text))"
        ),
    ),
)


async def ensure_startup_indexes(engine: AsyncEngine) -> None:
    """Create auxiliary indexes if they are missing. Best-effort, non-fatal."""
    async with engine.begin() as conn:
        for index_name, ddl in _STARTUP_INDEXES:
            try:
                await conn.execute(sql_text(ddl))
            except Exception as exc:  # noqa: BLE001 — never block startup over an index
                logger.warning("Skipping index %s: %s", index_name, exc)
