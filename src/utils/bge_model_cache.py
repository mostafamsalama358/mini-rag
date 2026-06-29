"""Process-wide singleton cache for local BGE models.

Each OS process loads at most one FlagEmbedding model per unique config key.
Inference is serialized with a lock so concurrent Celery threads or
``asyncio.to_thread`` calls do not run overlapping forward passes on CPU.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_cache_lock = threading.Lock()
_embedding_models: dict[tuple[str, bool], Any] = {}
_reranker_models: dict[tuple[str, str, bool], Any] = {}
_embedding_inference_lock = threading.Lock()
_reranker_inference_lock = threading.Lock()


def _ensure_hf_auth() -> None:
    from helpers.config import get_settings
    from helpers.hf_auth import configure_hf_from_settings

    configure_hf_from_settings(get_settings())


def get_bge_embedding_model(model_id: str, *, use_fp16: bool = True) -> tuple[Any, float]:
    """Return a cached ``BGEM3FlagModel`` and load duration (0 on cache hit)."""
    _ensure_hf_auth()
    key = (model_id, use_fp16)
    with _cache_lock:
        cached = _embedding_models.get(key)
        if cached is not None:
            return cached, 0.0

        from FlagEmbedding import BGEM3FlagModel

        load_started = time.perf_counter()
        model = BGEM3FlagModel(model_id, use_fp16=use_fp16)
        load_elapsed = time.perf_counter() - load_started
        _embedding_models[key] = model
        logger.info(
            "Loaded BGE embedding model: %s in %.2fs (cache miss)",
            model_id,
            load_elapsed,
        )
        return model, load_elapsed


def get_bge_reranker_model(
    model_name: str,
    *,
    device: str,
    use_fp16: bool,
) -> tuple[Any, float]:
    """Return a cached ``FlagReranker`` and load duration (0 on cache hit)."""
    normalized_device = (device or "cpu").strip()
    key = (model_name, normalized_device, use_fp16)
    with _cache_lock:
        cached = _reranker_models.get(key)
        if cached is not None:
            return cached, 0.0

        from FlagEmbedding import FlagReranker

        init_kwargs: dict[str, Any] = {"use_fp16": use_fp16}
        if normalized_device:
            init_kwargs["devices"] = [normalized_device]

        load_started = time.perf_counter()
        model = FlagReranker(model_name, **init_kwargs)
        load_elapsed = time.perf_counter() - load_started
        _reranker_models[key] = model
        logger.info(
            "Loaded BGE reranker model: %s on %s in %.2fs (cache miss)",
            model_name,
            normalized_device,
            load_elapsed,
        )
        return model, load_elapsed


def run_bge_embedding_inference(fn: Callable[[], T]) -> T:
    with _embedding_inference_lock:
        return fn()


def run_bge_reranker_inference(fn: Callable[[], T]) -> T:
    with _reranker_inference_lock:
        return fn()
