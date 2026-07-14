"""Strategy registries for Knowledge Representation components."""

from __future__ import annotations

from typing import TypeVar

from core.knowledge.errors import StrategyNotFoundError
from core.knowledge.interfaces import (
    KnowledgeNormalizer,
    KnowledgeRepresentationStrategy,
    KnowledgeUnitExtractor,
    RelationshipDiscoverer,
)

T = TypeVar("T")


class _Registry:
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: dict[str, object] = {}

    def register(self, strategy_id: str, impl: object) -> None:
        self._items[strategy_id] = impl

    def get(self, strategy_id: str) -> object:
        if strategy_id not in self._items:
            raise StrategyNotFoundError(
                f"unknown {self._kind} strategy: {strategy_id!r}"
            )
        return self._items[strategy_id]

    def clear(self) -> None:
        self._items.clear()

    def ids(self) -> list[str]:
        return sorted(self._items)


ExtractorRegistry = _Registry("extractor")
NormalizerRegistry = _Registry("normalizer")
DiscovererRegistry = _Registry("discoverer")
RepresentationStrategyRegistry = _Registry("representation")

# Module-level singletons used by the factory.
extractor_registry = ExtractorRegistry
normalizer_registry = NormalizerRegistry
discoverer_registry = DiscovererRegistry
representation_strategy_registry = RepresentationStrategyRegistry


_DEFAULTS_REGISTERED = False


def register_defaults() -> None:
    """Register built-in strategies. Safe to call multiple times."""
    global _DEFAULTS_REGISTERED
    if _DEFAULTS_REGISTERED:
        return
    from core.knowledge.discovery import StubNoOpDiscoverer
    from core.knowledge.discovery.structural import StructuralRelationshipDiscoverer
    from core.knowledge.extractors.structural import StructuralKnowledgeUnitExtractor
    from core.knowledge.normalizers import StubPassthroughNormalizer
    from core.knowledge.normalizers.rule_based import RuleBasedKnowledgeNormalizer
    from core.knowledge.representation.base import (
        NoOpRepresentationStrategy,
        StubGraphRepresentationStrategy,
        StubRelationalRepresentationStrategy,
    )

    extractor_registry.register("structural", StructuralKnowledgeUnitExtractor())
    normalizer_registry.register("rule_based", RuleBasedKnowledgeNormalizer())
    normalizer_registry.register("passthrough", StubPassthroughNormalizer())
    discoverer_registry.register("structural", StructuralRelationshipDiscoverer())
    discoverer_registry.register("noop", StubNoOpDiscoverer())
    representation_strategy_registry.register("noop", NoOpRepresentationStrategy())
    representation_strategy_registry.register(
        "stub_graph", StubGraphRepresentationStrategy()
    )
    representation_strategy_registry.register(
        "stub_relational", StubRelationalRepresentationStrategy()
    )
    _DEFAULTS_REGISTERED = True


def get_extractor(strategy_id: str) -> KnowledgeUnitExtractor:
    return extractor_registry.get(strategy_id)  # type: ignore[return-value]


def get_normalizer(strategy_id: str) -> KnowledgeNormalizer:
    return normalizer_registry.get(strategy_id)  # type: ignore[return-value]


def get_discoverer(strategy_id: str) -> RelationshipDiscoverer:
    return discoverer_registry.get(strategy_id)  # type: ignore[return-value]


def get_representation_strategy(strategy_id: str) -> KnowledgeRepresentationStrategy:
    return representation_strategy_registry.get(strategy_id)  # type: ignore[return-value]
