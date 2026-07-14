"""Base retriever helpers."""

from __future__ import annotations

import logging
import time
from abc import ABC

from core.retrieval_engine.interfaces import IRetriever
from core.retrieval_engine.models import RetrievalContext, RetrievalQuery

logger = logging.getLogger(__name__)


class BaseRetriever(IRetriever, ABC):
    _retriever_id: str = "base"
    _supported_strategy: str = "semantic"
    _sequential_only: bool = False
    _experimental: bool = False

    @property
    def retriever_id(self) -> str:
        return self._retriever_id

    @property
    def supported_strategy(self) -> str:
        return self._supported_strategy

    @property
    def sequential_only(self) -> bool:
        return self._sequential_only

    @property
    def experimental(self) -> bool:
        return self._experimental

    def _log_retrieve_start(
        self, query: RetrievalQuery, context: RetrievalContext
    ) -> float:
        logger.debug(
            "retrieve_start retriever_id=%s strategy=%s plan_id=%s variant=%s",
            self.retriever_id,
            query.strategy,
            context.plan_id,
            query.expander_variant_id,
        )
        return time.perf_counter()

    def _log_retrieve_end(
        self, query: RetrievalQuery, count: int, latency_ms: float
    ) -> None:
        logger.debug(
            "retrieve_end retriever_id=%s strategy=%s count=%s latency_ms=%.2f",
            self.retriever_id,
            query.strategy,
            count,
            latency_ms,
        )
