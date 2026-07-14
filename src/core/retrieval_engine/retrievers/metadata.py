"""Metadata filter retriever — strategy=metadata."""

from __future__ import annotations

import time
from typing import Any

from core.retrieval_engine.models import RawCandidate, RetrievalContext, RetrievalQuery, SourceRef
from core.retrieval_engine.retrievers.base import BaseRetriever


class MetadataRetriever(BaseRetriever):
    _retriever_id = "metadata_filter"
    _supported_strategy = "metadata"

    def __init__(self, metadata_store: Any = None) -> None:
        self._store = metadata_store

    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]:
        started = self._log_retrieve_start(query, context)
        results: list[Any] = []
        if self._store is not None:
            search = getattr(self._store, "search", None) or getattr(
                self._store, "filter_search", None
            )
            if search is not None:
                maybe = search(query.query_text, filters=context.filters)
                if hasattr(maybe, "__await__"):
                    results = await maybe
                else:
                    results = maybe or []
        candidates = [_to_raw(r, self.retriever_id, query) for r in results]
        latency_ms = (time.perf_counter() - started) * 1000.0
        self._log_retrieve_end(query, len(candidates), latency_ms)
        return candidates


def _to_raw(item: Any, retriever_id: str, query: RetrievalQuery) -> RawCandidate:
    if isinstance(item, RawCandidate):
        return item
    if isinstance(item, dict):
        chunk_id = str(item.get("chunk_id", item.get("id", "")))
        document_id = str(item.get("document_id", item.get("doc_id", "")))
        score = float(item.get("score", item.get("raw_score", 0.0)))
        excerpt = str(item.get("content_excerpt", item.get("text", "")))
        source_ref = item.get("source_ref")
        if source_ref is None and document_id and chunk_id:
            source_ref = SourceRef(document_id=document_id, chunk_id=chunk_id)
        elif isinstance(source_ref, dict):
            source_ref = SourceRef(**source_ref)
        return RawCandidate(
            chunk_id=chunk_id,
            document_id=document_id,
            raw_score=score,
            retriever_id=retriever_id,
            strategy=query.strategy,
            expander_variant_id=query.expander_variant_id,
            content_excerpt=excerpt,
            source_ref=source_ref,
        )
    raise TypeError(f"unsupported metadata store result type: {type(item)!r}")
