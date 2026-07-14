"""Stable interfaces for Knowledge Representation strategies (spec 008)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from core.chunking.models import ChunkSet
from core.knowledge.models import (
    KnowledgeExtractionConfig,
    KnowledgePackage,
    KnowledgeRelationship,
    KnowledgeUnit,
    RelationshipCandidate,
)


class KnowledgeUnitExtractor(ABC):
    """Pluggable extraction strategy: ChunkSet → KnowledgeUnits."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique registered name for this strategy."""
        ...

    @abstractmethod
    def extract(
        self,
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]:
        """Extract one or more KnowledgeUnits from each Chunk."""
        ...


class KnowledgeNormalizer(ABC):
    """Pluggable normalization strategy: raw KUs → normalized KUs."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique registered name for this strategy."""
        ...

    @abstractmethod
    def normalize(
        self,
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]:
        """Normalize and deduplicate KnowledgeUnits without inventing knowledge."""
        ...


class RelationshipDiscoverer(ABC):
    """Two-stage relationship discovery: candidates then validated relationships."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique registered name for this strategy."""
        ...

    @abstractmethod
    def generate_candidates(
        self,
        units: list[KnowledgeUnit],
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[RelationshipCandidate]:
        """Produce intermediate RelationshipCandidate entities."""
        ...

    @abstractmethod
    def validate_candidates(
        self,
        candidates: list[RelationshipCandidate],
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeRelationship]:
        """Filter candidates into published KnowledgeRelationships."""
        ...


class KnowledgeRepresentationStrategy(Protocol):
    """Pure read-only projection of a KnowledgePackage into another format."""

    @property
    def strategy_id(self) -> str:
        """Unique registered name for this strategy."""
        ...

    def apply(self, package: KnowledgePackage) -> Any:
        """Return a representation artifact without mutating the package."""
        ...
