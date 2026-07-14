"""Strategy → retriever routing."""

from __future__ import annotations

from core.retrieval_engine.errors import RetrieverNotFoundError
from core.retrieval_engine.interfaces import IRetriever


class StrategyRouter:
    def __init__(self, get_retriever) -> None:
        self._get_retriever = get_retriever

    def route(self, strategy: str) -> IRetriever:
        assert strategy != "hybrid", (
            '"hybrid" is a pipeline meta-strategy and must not be passed to StrategyRouter'
        )
        retriever = self._get_retriever(strategy)
        if retriever is None:
            raise RetrieverNotFoundError(strategy)
        return retriever
