"""services/rag/embedding.py — query embedding helpers.

Split out of `NLPController` (003 refactor Phase 4c). The sync/async query
embedding surface used by the RAG pipeline. Behavior is unchanged — these are
pure extractions of the controller's `_embed_query*` / `_embed_primary_query`
methods into free functions that take the embedding client explicitly.

Adds request-scoped deduplication so identical query text is embedded at most
once per HTTP request, plus an optional small global LRU for repeated queries.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from stores.llm.LLMEnums import DocumentTypeEnum
from helpers.config import get_settings

logger = logging.getLogger(__name__)

_QUERY_DOC_TYPE = DocumentTypeEnum.QUERY.value

_embed_api_semaphore: asyncio.Semaphore | None = None
_embed_api_semaphore_lock = threading.Lock()


def _get_embed_api_semaphore() -> asyncio.Semaphore:
    global _embed_api_semaphore
    with _embed_api_semaphore_lock:
        if _embed_api_semaphore is None:
            limit = max(1, int(getattr(get_settings(), "EMBEDDING_MAX_CONCURRENT_API_CALLS", 1)))
            _embed_api_semaphore = asyncio.Semaphore(limit)
        return _embed_api_semaphore


def _cache_key(text: str, document_type: str | None) -> tuple[str, str]:
    return (text.strip(), document_type or _QUERY_DOC_TYPE)


def _first_vector(raw: Any) -> list[float] | None:
    if not isinstance(raw, list) or not raw:
        return None
    first = raw[0]
    if isinstance(first, (list, tuple)):
        return [float(x) for x in first]
    if all(isinstance(x, (int, float)) for x in raw):
        return [float(x) for x in raw]
    return None


def _vectors_from_batch(raw: Any) -> list[list[float] | None]:
    if not isinstance(raw, list) or not raw:
        return []
    if raw and isinstance(raw[0], (int, float)):
        vec = _first_vector(raw)
        return [vec] if vec else []
    out: list[list[float] | None] = []
    for item in raw:
        if isinstance(item, (list, tuple)):
            out.append([float(x) for x in item])
        else:
            out.append(None)
    return out


# ---- optional cross-request LRU (query text only) ----

_global_lock = threading.Lock()
_global_cache: OrderedDict[tuple[str, str], list[float]] = OrderedDict()


def _global_cache_get(key: tuple[str, str]) -> list[float] | None:
    settings = get_settings()
    if not getattr(settings, "EMBEDDING_GLOBAL_CACHE_ENABLED", True):
        return None
    with _global_lock:
        vec = _global_cache.get(key)
        if vec is not None:
            _global_cache.move_to_end(key)
        return vec


def _global_cache_put(key: tuple[str, str], vector: list[float]) -> None:
    settings = get_settings()
    if not getattr(settings, "EMBEDDING_GLOBAL_CACHE_ENABLED", True):
        return
    max_entries = int(getattr(settings, "EMBEDDING_GLOBAL_CACHE_MAX_ENTRIES", 256))
    with _global_lock:
        _global_cache[key] = vector
        _global_cache.move_to_end(key)
        while len(_global_cache) > max_entries:
            _global_cache.popitem(last=False)


# ---- request-scoped cache ----

@dataclass
class EmbeddingCache:
    """In-request dedup for embedding calls (safe under asyncio.gather)."""

    _vectors: dict[tuple[str, str], list[float]] = field(default_factory=dict)
    _inflight: dict[tuple[str, str], asyncio.Task] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def get_vector(self, text: str, *, document_type: str | None = None) -> list[float] | None:
        key = _cache_key(text, document_type)
        if not key[0]:
            return None
        return self._vectors.get(key)

    def store_vector(
        self,
        text: str,
        vector: list[float],
        *,
        document_type: str | None = None,
    ) -> None:
        key = _cache_key(text, document_type)
        if key[0] and vector:
            self._vectors[key] = vector
            _global_cache_put(key, vector)

    async def embed_one(
        self,
        embedding_client,
        text: str,
        *,
        document_type: str | None = None,
    ) -> list[float] | None:
        key = _cache_key(text, document_type)
        if not key[0]:
            return None

        cached = self._vectors.get(key)
        if cached is not None:
            return cached

        global_hit = _global_cache_get(key)
        if global_hit is not None:
            self._vectors[key] = global_hit
            return global_hit

        async with self._lock:
            cached = self._vectors.get(key)
            if cached is not None:
                return cached
            global_hit = _global_cache_get(key)
            if global_hit is not None:
                self._vectors[key] = global_hit
                return global_hit
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(
                    _embed_raw_async(embedding_client, key[0], document_type=key[1])
                )
                self._inflight[key] = task

        try:
            vector = await task
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

        if vector is not None:
            self._vectors[key] = vector
            _global_cache_put(key, vector)
        return vector

    async def embed_many(
        self,
        embedding_client,
        texts: list[str],
        *,
        document_type: str | None = None,
    ) -> dict[str, list[float]]:
        doc_type = document_type or _QUERY_DOC_TYPE
        unique = list(dict.fromkeys(t.strip() for t in texts if t and t.strip()))
        found: dict[str, list[float]] = {}
        missing: list[str] = []

        for text in unique:
            key = _cache_key(text, doc_type)
            cached = self._vectors.get(key)
            if cached is not None:
                found[text] = cached
                continue
            global_hit = _global_cache_get(key)
            if global_hit is not None:
                self._vectors[key] = global_hit
                found[text] = global_hit
                continue
            missing.append(text)

        if missing:
            batch = await _embed_batch_async(embedding_client, missing, document_type=doc_type)
            for text, vector in zip(missing, batch):
                if vector is None:
                    continue
                key = _cache_key(text, doc_type)
                self._vectors[key] = vector
                _global_cache_put(key, vector)
                found[text] = vector

        return found


def intent_examples_cache_key(config) -> str:
    """Stable key for intent example phrase vectors (shared across requests)."""
    parts: list[str] = []
    for name in sorted(config.rules.keys()):
        phrases = tuple(sorted(config.rules[name].examples))
        parts.append(f"{name}={'|'.join(phrases)}")
    payload = "\n".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_intent_example_vectors: dict[str, dict[str, list[list[float]]]] = {}
_intent_example_lock = asyncio.Lock()


async def get_intent_example_vectors(config, embedding_client, cache: EmbeddingCache | None = None):
    """Return intent example vectors, computing once per unique phrase set."""
    key = intent_examples_cache_key(config)
    if config._example_vectors is not None:
        return config._example_vectors

    async with _intent_example_lock:
        if key in _intent_example_vectors:
            config._example_vectors = _intent_example_vectors[key]
            return config._example_vectors

        vectors: dict[str, list[list[float]]] = {}
        phrase_lists: list[tuple[str, str]] = []
        for name, rule in config.rules.items():
            for phrase in rule.examples:
                phrase_lists.append((name, phrase))

        if not phrase_lists:
            config._example_vectors = vectors
            _intent_example_vectors[key] = vectors
            return vectors

        unique_phrases = list(dict.fromkeys(p for _, p in phrase_lists))
        if cache is not None:
            embedded = await cache.embed_many(
                embedding_client, unique_phrases, document_type=_QUERY_DOC_TYPE
            )
        else:
            batch = await _embed_batch_async(embedding_client, unique_phrases, document_type=_QUERY_DOC_TYPE)
            embedded = {
                phrase: vec for phrase, vec in zip(unique_phrases, batch) if vec is not None
            }

        for intent_name, phrase in phrase_lists:
            vec = embedded.get(phrase)
            if vec:
                vectors.setdefault(intent_name, []).append(vec)

        config._example_vectors = vectors
        _intent_example_vectors[key] = vectors
        return vectors


async def _embed_raw_async(embedding_client, text: str, *, document_type: str) -> list[float] | None:
    try:
        async with _get_embed_api_semaphore():
            settings = get_settings()
            if settings.LLM_USE_ASYNC:
                raw = await _embed_query_async_uncached(
                    embedding_client, text, document_type=document_type
                )
            else:
                raw = await asyncio.to_thread(
                    embed_query, embedding_client, text, document_type=document_type
                )
        return _first_vector(raw)
    except Exception as exc:
        logger.warning("Embedding failed for %r: %s", text[:80], exc)
        return None


async def _embed_query_async_uncached(embedding_client, text: str, *, document_type: str):
    embed_async = getattr(embedding_client, "embed_text_async", None)
    if embed_async is not None:
        return await embed_async(text=text, document_type=document_type)
    return await asyncio.to_thread(
        embedding_client.embed_text,
        text=text,
        document_type=document_type,
    )


async def _embed_batch_async(
    embedding_client,
    texts: list[str],
    *,
    document_type: str,
) -> list[list[float] | None]:
    if not texts:
        return []

    settings = get_settings()
    batch_size = max(1, int(getattr(settings, "EMBEDDING_BATCH_SIZE", 32)))
    results: list[list[float] | None] = []

    try:
        async with _get_embed_api_semaphore():
            for offset in range(0, len(texts), batch_size):
                chunk = texts[offset : offset + batch_size]
                embed_async = getattr(embedding_client, "embed_text_async", None)
                embed_sync = getattr(embedding_client, "embed_text", None)

                if settings.LLM_USE_ASYNC and embed_async is not None:
                    raw = await embed_async(text=chunk, document_type=document_type)
                elif embed_sync is not None:
                    raw = await asyncio.to_thread(
                        embed_sync, text=chunk, document_type=document_type
                    )
                else:
                    raw = None

                results.extend(_vectors_from_batch(raw))
                if offset + batch_size < len(texts):
                    delay = float(getattr(settings, "VERTEX_EMBEDDING_BATCH_DELAY_SECONDS", 0.5))
                    if delay > 0:
                        await asyncio.sleep(delay)
    except Exception as exc:
        logger.warning("Batch embedding failed (%d texts): %s", len(texts), exc)
        if not results:
            return [None] * len(texts)
        results.extend([None] * (len(texts) - len(results)))

    if len(results) < len(texts):
        results.extend([None] * (len(texts) - len(results)))
    return results[: len(texts)]


def embed_query(embedding_client, text: str, *, document_type: str | None = None):
    """Embed a query using the sync embedding client."""
    try:
        return embedding_client.embed_text(
            text=text,
            document_type=document_type or _QUERY_DOC_TYPE,
        )
    except Exception as exc:
        logger.warning("Sync embedding failed: %s", exc)
        return None


async def embed_query_async(
    embedding_client,
    text: str,
    *,
    document_type: str | None = None,
    cache: EmbeddingCache | None = None,
):
    """Embed a query without blocking the event loop when an async client exists."""
    doc_type = document_type or _QUERY_DOC_TYPE
    if cache is not None and isinstance(text, str):
        vector = await cache.embed_one(embedding_client, text, document_type=doc_type)
        return [vector] if vector is not None else None

    try:
        async with _get_embed_api_semaphore():
            return await _embed_query_async_uncached(
                embedding_client, text, document_type=doc_type
            )
    except Exception as exc:
        logger.warning("Async embedding failed for %r: %s", str(text)[:80], exc)
        return None


async def embed_primary_query(
    embedding_client,
    text: str,
    *,
    cache: EmbeddingCache | None = None,
) -> list | None:
    if cache is not None:
        return await cache.embed_one(embedding_client, text, document_type=_QUERY_DOC_TYPE)

    settings = get_settings()
    if settings.LLM_USE_ASYNC:
        vectors = await embed_query_async(embedding_client, text)
    else:
        vectors = embed_query(embedding_client, text)
    return vectors[0] if isinstance(vectors, list) and vectors else None
