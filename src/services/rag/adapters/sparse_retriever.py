"""PgVector sparse / FTS retriever adapter (spec 015)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from core.retrieval_engine.interfaces import IRetriever
from core.retrieval_engine.models import RawCandidate, RetrievalContext, RetrievalQuery
from helpers.config import get_settings
from services.rag.adapters.capabilities import AdapterCapabilities
from services.rag.adapters.scope import (
    ScopeMissReason,
    allow_unscoped_degrade,
    apply_field_score_boost,
    classify_scoped_miss,
    log_scoped_miss,
    merge_retrieved_docs,
    per_entity_fetch_limit,
    resolve_entity_prefixes,
)
from services.rag.adapters.type_mapping import retrieved_document_to_raw_candidate
from services.rag.adapters.vector_retriever import (
    _fetch_limit,
    _is_transient,
    _needs_scoped,
    _scope_from_metadata,
    resolve_collection_name,
)
from stores.vectordb.providers.pgvector.search import brand_head_fallback_prefix

logger = logging.getLogger("uvicorn.error")


class PgVectorSparseRetriever(IRetriever):
    """Sparse / keyword search via search_by_text[_scoped]."""

    CAPABILITIES = AdapterCapabilities(
        retriever_id="pgvector_sparse",
        supported_strategy="sparse",
        features=frozenset({"sparse_text", "scoped_search", "metadata_filter"}),
    )

    def __init__(
        self,
        *,
        vectordb_client: Any,
        embedding_client: Any | None = None,
        collection_resolver: Callable[[RetrievalContext], str | None] | None = None,
        max_transient_attempts: int = 2,
    ) -> None:
        self._vectordb = vectordb_client
        self._embedding = embedding_client
        self._collection_resolver = collection_resolver
        self._max_attempts = max(1, int(max_transient_attempts))

    @property
    def retriever_id(self) -> str:
        return self.CAPABILITIES.retriever_id

    @property
    def supported_strategy(self) -> str:
        return self.CAPABILITIES.supported_strategy

    def _resolve_collection(self, context: RetrievalContext) -> str | None:
        if self._collection_resolver is not None:
            return self._collection_resolver(context)
        return resolve_collection_name(
            context.metadata or {},
            vectordb_client=self._vectordb,
            embedding_client=self._embedding,
        )

    async def _search_unscoped(
        self,
        *,
        collection_name: str,
        text: str,
        limit: int,
    ) -> list[Any]:
        if not hasattr(self._vectordb, "search_by_text"):
            return []
        return (
            await self._vectordb.search_by_text(
                collection_name=collection_name,
                query=text,
                limit=limit,
            )
            or []
        )

    async def _search_scoped_single(
        self,
        *,
        collection_name: str,
        text: str,
        limit: int,
        scope: dict[str, Any],
    ) -> list[Any] | bool:
        docs = await self._vectordb.search_by_text_scoped(
            collection_name=collection_name,
            query=text,
            limit=limit,
            entity_key=scope.get("entity_key"),
            entity_prefix=scope.get("entity_prefix"),
            entity_prefixes=scope.get("entity_prefixes"),
            field_key=scope.get("field_key"),
            metadata_filter=scope.get("metadata_filter"),
        )
        if docs is False:
            return False
        if docs:
            return list(docs)
        if scope.get("field_key") and (
            scope.get("entity_prefix") or scope.get("entity_prefixes")
        ):
            logger.info(
                "pgvector_sparse_field_soft_miss field_key=%r entity_prefixes=%r",
                scope.get("field_key"),
                scope.get("entity_prefixes") or [scope.get("entity_prefix")],
            )
            soft_docs = await self._vectordb.search_by_text_scoped(
                collection_name=collection_name,
                query=text,
                limit=limit,
                entity_key=scope.get("entity_key"),
                entity_prefix=scope.get("entity_prefix"),
                entity_prefixes=scope.get("entity_prefixes"),
                field_key=None,
                metadata_filter=scope.get("metadata_filter"),
            )
            if soft_docs:
                return list(soft_docs)
        head = brand_head_fallback_prefix(str(scope.get("entity_prefix") or ""))
        if head:
            logger.info(
                "pgvector_sparse_brand_head_fallback from=%r to=%r",
                scope.get("entity_prefix"),
                head,
            )
            head_docs = await self._vectordb.search_by_text_scoped(
                collection_name=collection_name,
                query=text,
                limit=limit,
                entity_key=scope.get("entity_key"),
                entity_prefix=head,
                field_key=scope.get("field_key"),
                metadata_filter=scope.get("metadata_filter"),
            )
            if head_docs:
                return list(head_docs)
            if scope.get("field_key"):
                head_soft = await self._vectordb.search_by_text_scoped(
                    collection_name=collection_name,
                    query=text,
                    limit=limit,
                    entity_key=scope.get("entity_key"),
                    entity_prefix=head,
                    field_key=None,
                    metadata_filter=scope.get("metadata_filter"),
                )
                if head_soft:
                    return list(head_soft)
        return []

    async def _search_once(
        self,
        *,
        collection_name: str,
        text: str,
        limit: int,
        scope: dict[str, Any],
    ) -> list[Any]:
        if _needs_scoped(scope) and hasattr(self._vectordb, "search_by_text_scoped"):
            prefixes = resolve_entity_prefixes(scope)
            if len(prefixes) > 1:
                per = per_entity_fetch_limit(limit, len(prefixes))
                total_cap = min(max(limit, per * len(prefixes)), 60)
                logger.info(
                    "pgvector_sparse_multi_entity_fanout entities=%s per_limit=%s",
                    prefixes,
                    per,
                )
                buckets: list[list[Any]] = []
                for prefix in prefixes:
                    sub = {
                        "entity_key": scope.get("entity_key"),
                        "entity_prefix": prefix,
                        "entity_prefixes": None,
                        "field_key": scope.get("field_key"),
                        "metadata_filter": scope.get("metadata_filter"),
                    }
                    part = await self._search_scoped_single(
                        collection_name=collection_name,
                        text=text,
                        limit=per,
                        scope=sub,
                    )
                    if part is False:
                        log_scoped_miss(
                            channel="pgvector_sparse",
                            collection_name=collection_name,
                            scope=scope,
                            reason=ScopeMissReason.COLLECTION_MISSING,
                            degraded=False,
                        )
                        return []
                    if part:
                        buckets.append(list(part))
                merged = merge_retrieved_docs(buckets, limit=total_cap)
                if merged:
                    return merged
                reason = classify_scoped_miss(scope)
                degrade = allow_unscoped_degrade()
                log_scoped_miss(
                    channel="pgvector_sparse",
                    collection_name=collection_name,
                    scope=scope,
                    reason=reason,
                    degraded=degrade,
                )
                if not degrade:
                    return []
                return await self._search_unscoped(
                    collection_name=collection_name,
                    text=text,
                    limit=limit,
                )

            docs = await self._search_scoped_single(
                collection_name=collection_name,
                text=text,
                limit=limit,
                scope=scope,
            )
            if docs is False:
                log_scoped_miss(
                    channel="pgvector_sparse",
                    collection_name=collection_name,
                    scope=scope,
                    reason=ScopeMissReason.COLLECTION_MISSING,
                    degraded=False,
                )
                return []
            if docs:
                return list(docs)
            reason = classify_scoped_miss(scope)
            degrade = allow_unscoped_degrade()
            log_scoped_miss(
                channel="pgvector_sparse",
                collection_name=collection_name,
                scope=scope,
                reason=reason,
                degraded=degrade,
            )
            if not degrade:
                return []
            return await self._search_unscoped(
                collection_name=collection_name,
                text=text,
                limit=limit,
            )
        return await self._search_unscoped(
            collection_name=collection_name,
            text=text,
            limit=limit,
        )

    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]:
        collection_name = self._resolve_collection(context)
        if not collection_name or not (query.query_text or "").strip():
            return []

        scope = _scope_from_metadata(context.metadata or {})
        limit = _fetch_limit(context)
        last_exc: BaseException | None = None

        for attempt in range(self._max_attempts):
            try:
                docs = await self._search_once(
                    collection_name=collection_name,
                    text=query.query_text,
                    limit=limit,
                    scope=scope,
                )
                settings = get_settings()
                docs = apply_field_score_boost(
                    list(docs or []),
                    field_key=scope.get("field_key"),
                    boost=float(getattr(settings, "RAG_FIELD_SCORE_BOOST", 0.15)),
                    penalty=float(getattr(settings, "RAG_FIELD_SCORE_PENALTY", 0.08)),
                )
                return [
                    retrieved_document_to_raw_candidate(
                        doc,
                        retriever_id=self.retriever_id,
                        strategy=query.strategy or self.supported_strategy,
                        expander_variant_id=query.expander_variant_id,
                    )
                    for doc in docs
                ]
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt + 1 < self._max_attempts and _is_transient(exc):
                    logger.warning(
                        "pgvector_sparse_transient_retry attempt=%s err=%s",
                        attempt + 1,
                        exc,
                    )
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        return []
