"""Experimental SQL retriever — strategy=sql.

This module is an **experimental extension point**. It is NOT registered in the
default RetrieverRegistry and requires explicit opt-in. SQL must use parameterized
queries only — never string-interpolate user query text into SQL.
"""

from __future__ import annotations

import time
from typing import Any

from core.retrieval_engine.models import RawCandidate, RetrievalContext, RetrievalQuery, SourceRef
from core.retrieval_engine.retrievers.base import BaseRetriever


class SQLRetriever(BaseRetriever):
    _retriever_id = "sql_retriever"
    _supported_strategy = "sql"
    _experimental = True

    def __init__(
        self,
        *,
        executor: Any = None,
        template_registry: dict[str, str] | None = None,
        default_template: str = "default",
    ) -> None:
        self._executor = executor
        self._templates = template_registry or {}
        self._default_template = default_template

    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]:
        started = self._log_retrieve_start(query, context)
        results: list[Any] = []
        sql_template = self._templates.get(self._default_template)
        if self._executor is not None and sql_template is not None:
            # Parameterized only — bind query text as a parameter, never interpolate.
            params = {"query_text": query.query_text, "plan_id": context.plan_id}
            execute = getattr(self._executor, "execute", None)
            if execute is not None:
                maybe = execute(sql_template, params)
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
    raise TypeError(f"unsupported sql result type: {type(item)!r}")
