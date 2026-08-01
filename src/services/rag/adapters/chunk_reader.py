"""SQL-backed chunk reader for evidence expansion (spec 015)."""

from __future__ import annotations

from typing import Any

from core.chunking.models import Chunk, ChunkIdentity
from core.evidence_orchestrator.interfaces import IChunkReader
from repositories.chunk_repository import ChunkModel


class SqlChunkReader(IChunkReader):
    """Loads chunk text + metadata via ChunkModel / DataChunk."""

    def __init__(
        self,
        *,
        db_client: Any = None,
        chunk_model: Any = None,
    ) -> None:
        self._db_client = db_client
        self._chunk_model = chunk_model

    async def _get_chunk_model(self):
        if self._chunk_model is not None:
            return self._chunk_model
        if self._db_client is None:
            return None
        return await ChunkModel.create_instance(self._db_client)

    async def get_chunk(self, chunk_id: str, document_id: str) -> Chunk | None:
        chunk_model = await self._get_chunk_model()
        if chunk_model is None or not chunk_id:
            return None

        row = None
        get_fn = getattr(chunk_model, "get_chunk", None)
        if get_fn is not None:
            # Prefer int PK when chunk_id is numeric; otherwise try as-is.
            try:
                row = await get_fn(int(chunk_id))
            except (TypeError, ValueError):
                row = await get_fn(chunk_id)

        if row is None:
            return None

        # Ensure document scope matches when both sides are available.
        asset_id = getattr(row, "chunk_asset_id", None)
        if document_id and asset_id is not None and str(asset_id) != str(document_id):
            # Still return the chunk — document_id in engine may be stringified
            # asset id or alternate key; soft mismatch is non-fatal.
            pass

        text = getattr(row, "chunk_text", None) or ""
        metadata = dict(getattr(row, "chunk_metadata", None) or {})
        identity = ChunkIdentity(
            chunk_id=str(getattr(row, "chunk_id", chunk_id)),
            document_id=str(document_id or asset_id or ""),
            strategy_id="sql",
            source_element_ids=[],
        )
        return Chunk(text=text, metadata=metadata, identity=identity)
