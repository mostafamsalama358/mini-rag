"""Retrieval strategy plugins resolved from SkillExecutionContext (022)."""

from __future__ import annotations

from services.rag.skills.strategies.base import RetrievalStrategy
from services.rag.skills.strategies.default import DefaultRetrievalStrategy
from services.rag.skills.strategies.document_lookup import DocumentLookupRetrievalStrategy
from services.rag.skills.strategies.hybrid import HybridRetrievalStrategy
from services.rag.skills.strategies.pair_lookup import PairLookupRetrievalStrategy
from services.rag.skills.strategies.registry import StrategyRegistry
from services.rag.skills.strategies.semantic_only import SemanticOnlyRetrievalStrategy

_DEFAULT_STRATEGIES: tuple[RetrievalStrategy, ...] = (
    DefaultRetrievalStrategy(),
    PairLookupRetrievalStrategy(),
    DocumentLookupRetrievalStrategy(),
    SemanticOnlyRetrievalStrategy(),
    HybridRetrievalStrategy(),
)

_registry = StrategyRegistry()
for _strategy in _DEFAULT_STRATEGIES:
    _registry.register(_strategy)


def register_strategy(strategy: RetrievalStrategy) -> None:
    """Register a custom retrieval strategy (Open/Closed extension point)."""
    _registry.register(strategy)


def get_retrieval_strategy(name: str) -> RetrievalStrategy:
    return _registry.get(name)


__all__ = [
    "DefaultRetrievalStrategy",
    "DocumentLookupRetrievalStrategy",
    "HybridRetrievalStrategy",
    "PairLookupRetrievalStrategy",
    "RetrievalStrategy",
    "SemanticOnlyRetrievalStrategy",
    "StrategyRegistry",
    "get_retrieval_strategy",
    "register_strategy",
]
