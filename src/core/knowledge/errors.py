"""Error types for the Knowledge Representation pipeline (spec 008)."""

from __future__ import annotations


class KnowledgeRepresentationError(Exception):
    """Base error for all Knowledge Representation failures."""


class EvidenceIntegrityError(KnowledgeRepresentationError, ValueError):
    """Raised when an EvidenceReference violates the four-level traceability chain."""


class StrategyNotFoundError(KnowledgeRepresentationError):
    """Raised when a requested strategy id is not registered."""


class KnowledgeValidationFailedError(KnowledgeRepresentationError):
    """Raised when validation fails and the caller configured fail-on-error."""
