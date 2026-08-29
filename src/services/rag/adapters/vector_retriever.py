"""PgVector dense retriever adapter (spec 015)."""

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
    field_soft_miss_eligible,
    log_scoped_miss,
    merge_retrieved_docs,
    per_entity_fetch_limit,
    resolve_entity_prefixes,
)
from services.rag.adapters.type_mapping import retrieved_document_to_raw_candidate
from stores.llm.LLMEnums import DocumentTypeEnum
from stores.vectordb.providers.pgvector.search import brand_head_fallback_prefix

logger = logging.getLogger("uvicorn.error")

_TRANSIENT_MARKERS = (
    "connection",
    "timeout",
    "timed out",
    "reset",
    "pool",
    "broken pipe",
    "temporarily unavailable",
    "unavailable",
    "operationalerror",
    "interfaceerror",
)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)):
        return False
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return any(marker in name or marker in msg for marker in _TRANSIENT_MARKERS)


def resolve_collection_name(
    metadata: dict[str, Any],
    *,
    vectordb_client: Any = None,
    embedding_client: Any = None,
) -> str | None:
    """Resolve project-scoped collection name from RetrievalContext.metadata."""
    explicit = metadata.get("collection_name")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    project_id = metadata.get("project_id")
    if project_id is None:
        return None

    size = None
    if vectordb_client is not None:
        size = getattr(vectordb_client, "default_vector_size", None)
    if size is None and embedding_client is not None:
        size = getattr(embedding_client, "embedding_size", None)
    if size is None:
        return None
    return f"collection_{size}_{project_id}".strip()


def _scope_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    prefixes = metadata.get("entity_prefixes")
    if not isinstance(prefixes, list):
        prefixes = None
    return {
        "entity_key": metadata.get("entity_key"),
        "entity_prefix": metadata.get("entity_prefix"),
        "entity_prefixes": prefixes,
        "field_key": metadata.get("field_key"),
        "metadata_filter": metadata.get("metadata_filter"),
    }


def _needs_scoped(scope: dict[str, Any]) -> bool:
    # entity_prefix alone is enough: SQL layer defaults entity_key to "entity".
    return bool(
        scope.get("entity_prefix")
        or scope.get("entity_prefixes")
        or scope.get("field_key")
        or scope.get("metadata_filter")
    )


def _fetch_limit(context: RetrievalContext, default: int = 30) -> int:
    meta = context.metadata or {}
    raw = meta.get("limit") or meta.get("max_candidates") or default
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


class PgVectorDenseRetriever(IRetriever):
    """Dense vector search via pgvector / VectorDBInterface."""

    CAPABILITIES = AdapterCapabilities(
        retriever_id="pgvector_dense",
        supported_strategy="dense",
        features=frozenset({"dense_vector", "scoped_search", "metadata_filter"}),
    )

    def __init__(
        self,
        *,
        vectordb_client: Any,
        embedding_client: Any,
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

    async def _embed_query(self, text: str) -> list[float] | None:
        if not text:
            return None
        embed_async = getattr(self._embedding, "embed_text_async", None)
        if embed_async is not None:
            raw = await embed_async(
                text=text,
                document_type=DocumentTypeEnum.QUERY.value,
            )
        else:
            raw = await asyncio.to_thread(
                self._embedding.embed_text,
                text=text,
                document_type=DocumentTypeEnum.QUERY.value,
            )
        if isinstance(raw, list) and raw and isinstance(raw[0], (int, float)):
            return [float(x) for x in raw]
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            return [float(x) for x in raw[0]]
        return None

    async def _search_unscoped(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
    ) -> list[Any]:
        return (
            await self._vectordb.search_by_vector(
                collection_name=collection_name,
                vector=vector,
                limit=limit,
            )
            or []
        )

    async def _search_scoped_single(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
        scope: dict[str, Any],
    ) -> list[Any] | bool:
        """Scoped search for one entity (or OR-list). False = collection missing."""
        docs = await self._vectordb.search_by_vector_scoped(
            collection_name=collection_name,
            vector=vector,
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
        if field_soft_miss_eligible(scope):
            logger.info(
                "pgvector_dense_field_soft_miss field_key=%r entity_prefixes=%r "
                "metadata_filter=%r",
                scope.get("field_key"),
                scope.get("entity_prefixes") or [scope.get("entity_prefix")],
                scope.get("metadata_filter"),
            )
            soft_docs = await self._vectordb.search_by_vector_scoped(
                collection_name=collection_name,
                vector=vector,
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
                "pgvector_dense_brand_head_fallback from=%r to=%r",
                scope.get("entity_prefix"),
                head,
            )
            head_docs = await self._vectordb.search_by_vector_scoped(
                collection_name=collection_name,
                vector=vector,
                limit=limit,
                entity_key=scope.get("entity_key"),
                entity_prefix=head,
                field_key=scope.get("field_key"),
                metadata_filter=scope.get("metadata_filter"),
            )
            if head_docs:
                return list(head_docs)
            if scope.get("field_key"):
                head_soft = await self._vectordb.search_by_vector_scoped(
                    collection_name=collection_name,
                    vector=vector,
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
        vector: list[float],
        limit: int,
        scope: dict[str, Any],
    ) -> list[Any]:
        if _needs_scoped(scope) and hasattr(self._vectordb, "search_by_vector_scoped"):
            prefixes = resolve_entity_prefixes(scope)
            # Compare / multi-brand: retrieve per entity so one brand cannot
            # starve the top-k (OR + global limit collapses to best embedding).
            if len(prefixes) > 1:
                per = per_entity_fetch_limit(limit, len(prefixes))
                total_cap = min(max(limit, per * len(prefixes)), 60)
                logger.info(
                    "pgvector_dense_multi_entity_fanout entities=%s per_limit=%s",
                    prefixes,
                    per,
                )
                buckets: list[list[Any]] = []
                any_collection = False
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
                        vector=vector,
                        limit=per,
                        scope=sub,
                    )
                    if part is False:
                        any_collection = False
                        break
                    any_collection = True
                    if part:
                        buckets.append(list(part))
                if not any_collection and not buckets:
                    log_scoped_miss(
                        channel="pgvector_dense",
                        collection_name=collection_name,
                        scope=scope,
                        reason=ScopeMissReason.COLLECTION_MISSING,
                        degraded=False,
                    )
                    return []
                merged = merge_retrieved_docs(buckets, limit=total_cap)
                if merged:
                    return merged
                reason = classify_scoped_miss(scope)
                degrade = allow_unscoped_degrade()
                log_scoped_miss(
                    channel="pgvector_dense",
                    collection_name=collection_name,
                    scope=scope,
                    reason=reason,
                    degraded=degrade,
                )
                if not degrade:
                    return []
                return await self._search_unscoped(
                    collection_name=collection_name,
                    vector=vector,
                    limit=limit,
                )

            docs = await self._search_scoped_single(
                collection_name=collection_name,
                vector=vector,
                limit=limit,
                scope=scope,
            )
            if docs is False:
                log_scoped_miss(
                    channel="pgvector_dense",
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
                channel="pgvector_dense",
                collection_name=collection_name,
                scope=scope,
                reason=reason,
                degraded=degrade,
            )
            if not degrade:
                return []
            return await self._search_unscoped(
                collection_name=collection_name,
                vector=vector,
                limit=limit,
            )
        return await self._search_unscoped(
            collection_name=collection_name,
            vector=vector,
            limit=limit,
        )

    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]:
        collection_name = self._resolve_collection(context)
        if not collection_name:
            logger.warning(
                "pgvector_dense_missing_collection plan_id=%s",
                context.plan_id,
            )
            return []

        vector = await self._embed_query(query.query_text)
        if not vector:
            return []

        scope = _scope_from_metadata(context.metadata or {})
        limit = _fetch_limit(context)
        last_exc: BaseException | None = None

        for attempt in range(self._max_attempts):
            try:
                docs = await self._search_once(
                    collection_name=collection_name,
                    vector=vector,
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
                        "pgvector_dense_transient_retry attempt=%s err=%s",
                        attempt + 1,
                        exc,
                    )
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        return []
