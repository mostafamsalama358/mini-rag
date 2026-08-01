"""Legacy reranker → IReranker adapter (spec 015)."""

from __future__ import annotations

import asyncio
from typing import Any

from core.retrieval_engine.interfaces import IReranker
from core.retrieval_engine.models import RawCandidate
from services.rag.adapters.type_mapping import (
    raw_candidate_to_retrieved_document,
    retrieved_document_to_raw_candidate,
)


class LegacyRerankerAdapter(IReranker):
    """Wraps utils.rerank.RerankerInterface behind the engine IReranker protocol."""

    def __init__(self, legacy_reranker: Any, *, reranker_id: str = "legacy") -> None:
        self._legacy = legacy_reranker
        self._reranker_id = reranker_id

    @property
    def reranker_id(self) -> str:
        return self._reranker_id

    async def rerank(
        self,
        query_text: str,
        candidates: list[RawCandidate],
    ) -> list[RawCandidate]:
        if not candidates or self._legacy is None:
            return list(candidates)

        docs = [raw_candidate_to_retrieved_document(c) for c in candidates]
        rerank_fn = getattr(self._legacy, "rerank", None)
        if rerank_fn is None:
            return list(candidates)

        maybe = rerank_fn(query_text, docs)
        if hasattr(maybe, "__await__"):
            ranked = await maybe
        else:
            ranked = await asyncio.to_thread(rerank_fn, query_text, docs)

        if not ranked:
            return list(candidates)

        out: list[RawCandidate] = []
        by_chunk = {c.chunk_id: c for c in candidates}
        for doc in ranked:
            meta = getattr(doc, "metadata", None) or {}
            chunk_id = str(meta.get("chunk_id") or "")
            base = by_chunk.get(chunk_id)
            mapped = retrieved_document_to_raw_candidate(
                doc,
                retriever_id=(base.retriever_id if base else "legacy"),
                strategy=(base.strategy if base else "semantic"),
                expander_variant_id=(base.expander_variant_id if base else "primary"),
            )
            out.append(mapped)
        return out
