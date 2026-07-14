"""Relationship discovery strategies."""

from __future__ import annotations

from core.chunking.models import ChunkSet
from core.knowledge.discovery.structural import StructuralRelationshipDiscoverer
from core.knowledge.interfaces import RelationshipDiscoverer
from core.knowledge.models import (
    KnowledgeExtractionConfig,
    KnowledgeRelationship,
    KnowledgeUnit,
    RelationshipCandidate,
)

__all__ = ["StructuralRelationshipDiscoverer", "StubNoOpDiscoverer"]


class StubNoOpDiscoverer(RelationshipDiscoverer):
    """Returns empty candidates/relationships — useful for isolation tests."""

    @property
    def strategy_id(self) -> str:
        return "noop"

    def generate_candidates(
        self,
        units: list[KnowledgeUnit],
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[RelationshipCandidate]:
        _ = units, chunk_set, config
        return []

    def validate_candidates(
        self,
        candidates: list[RelationshipCandidate],
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeRelationship]:
        _ = candidates, units, config
        return []
