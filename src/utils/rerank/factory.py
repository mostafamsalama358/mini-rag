"""Factory: build the active reranker from Settings.

Returns a ``NoOpReranker`` by default (when ``RAG_ENABLE_RERANKER=false``),
so call sites don't need to check whether reranking is on before calling
``reranker.rerank()``.

Supported values for ``RAG_RERANKER_BACKEND``:
    - ``"cohere"``   — Cohere Rerank API (default)
    - ``"bge"``      — BAAI BGE Reranker (local)
    - anything else  — no-op (logs a warning)
"""

from __future__ import annotations

import logging
import threading

from .interface import RerankerInterface
from .noop import NoOpReranker

logger = logging.getLogger(__name__)

_bge_reranker_cache: dict[tuple, RerankerInterface] = {}
_bge_reranker_cache_lock = threading.Lock()


def get_reranker(settings=None) -> RerankerInterface:
    """Instantiate and return the configured reranker.

    Parameters
    ----------
    settings:
        A ``Settings`` instance (or any object with ``RAG_ENABLE_RERANKER``,
        ``RAG_RERANKER_BACKEND``, and ``COHERE_API_KEY`` attributes).
        Calls ``get_settings()`` from ``helpers.config`` when not provided.
    """
    if settings is None:
        from helpers.config import get_settings
        settings = get_settings()

    if not getattr(settings, "RAG_ENABLE_RERANKER", False):
        return NoOpReranker()

    backend = (getattr(settings, "RAG_RERANKER_BACKEND", "cohere") or "cohere").lower().strip()

    if backend == "cohere":
        api_key = getattr(settings, "COHERE_API_KEY", None)
        if not api_key:
            logger.warning(
                "RAG_ENABLE_RERANKER=true with RAG_RERANKER_BACKEND=cohere but "
                "COHERE_API_KEY is not set — falling back to no-op reranker."
            )
            return NoOpReranker()

        model = getattr(settings, "COHERE_RERANKER_MODEL", None) or "rerank-multilingual-v3.0"
        top_n = getattr(settings, "RAG_RERANKER_TOP_N", None)

        from .cohere_reranker import CohereReranker
        return CohereReranker(api_key=api_key, model=model, top_n=top_n)

    if backend == "bge":
        model = getattr(settings, "BGE_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        top_n = getattr(settings, "RAG_RERANKER_TOP_N", None)
        device = getattr(settings, "RAG_RERANKER_DEVICE", "cpu")
        batch_size = getattr(settings, "RAG_RERANKER_BATCH_SIZE", 16)
        use_fp16 = getattr(settings, "RAG_RERANKER_USE_FP16", False)
        max_chars = getattr(settings, "RAG_RERANKER_MAX_CHARS", 1024)
        
        cache_key = (model, top_n, device, batch_size, use_fp16, max_chars)
        with _bge_reranker_cache_lock:
            cached = _bge_reranker_cache.get(cache_key)
            if cached is not None:
                return cached

            from .bge_reranker import BgeReranker

            reranker = BgeReranker(
                model_name=model,
                top_n=top_n,
                device=device,
                batch_size=batch_size,
                use_fp16=use_fp16,
                max_chars=max_chars,
            )
            _bge_reranker_cache[cache_key] = reranker
            return reranker

    logger.warning(
        f"Unknown RAG_RERANKER_BACKEND={backend!r} — falling back to no-op reranker. "
        "Supported values: 'cohere', 'bge'."
    )
    return NoOpReranker()
