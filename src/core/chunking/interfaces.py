"""Stable interfaces for chunking strategies and boundary decision policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from core.chunking.models import (
    BoundaryCandidate,
    BoundaryDecision,
    BoundaryFeatures,
    ChunkingStrategyConfig,
    ChunkSet,
)
from core.document_intelligence.model import DocumentModel


class ChunkingStrategy(ABC):
    """Stable interface for every chunking strategy implementation."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique registered name for this strategy."""
        ...

    @abstractmethod
    def chunk(
        self,
        document_model: DocumentModel,
        config: ChunkingStrategyConfig,
    ) -> ChunkSet:
        """Produce a validated ChunkSet from the given DocumentModel."""
        ...


class BoundaryDecisionPolicy(Protocol):
    """Stable interface for boundary decision policy implementations."""

    def decide(
        self,
        candidate: BoundaryCandidate,
        features: BoundaryFeatures,
    ) -> BoundaryDecision:
        """Decide merge or split for one boundary candidate."""
        ...
