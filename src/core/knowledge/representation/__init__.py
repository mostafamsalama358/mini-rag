"""Optional knowledge representation strategies (read-only projections)."""

from core.knowledge.representation.base import (
    KnowledgeRepresentationStrategy,
    NoOpRepresentationStrategy,
    StubGraphRepresentationStrategy,
    StubRelationalRepresentationStrategy,
)

__all__ = [
    "KnowledgeRepresentationStrategy",
    "NoOpRepresentationStrategy",
    "StubGraphRepresentationStrategy",
    "StubRelationalRepresentationStrategy",
]
