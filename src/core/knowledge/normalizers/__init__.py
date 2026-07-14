"""Knowledge unit normalizers."""

from __future__ import annotations

from core.knowledge.interfaces import KnowledgeNormalizer
from core.knowledge.models import KnowledgeExtractionConfig, KnowledgeUnit
from core.knowledge.normalizers.rule_based import RuleBasedKnowledgeNormalizer

__all__ = ["RuleBasedKnowledgeNormalizer", "StubPassthroughNormalizer"]


class StubPassthroughNormalizer(KnowledgeNormalizer):
    """Identity normalizer for testing — returns input unchanged."""

    @property
    def strategy_id(self) -> str:
        return "passthrough"

    def normalize(
        self,
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]:
        _ = config
        return list(units)
