"""Retrieval Engine error hierarchy."""

from __future__ import annotations


class RetrievalEngineError(Exception):
    """Base error for all Retrieval Engine failures."""


class SchemaMismatchError(RetrievalEngineError):
    """RetrievalPlan schema major version is unsupported."""


class RetrieverNotFoundError(RetrievalEngineError):
    """No retriever registered for the requested strategy."""


class FusionError(RetrievalEngineError):
    """Score fusion failed."""


class InsufficientCandidatesError(RetrievalEngineError):
    """Result does not meet PartialResultPolicy.min_candidates_required."""


class RetrievalConstraintViolation(RetrievalEngineError):
    """A retrieval constraint could not be satisfied."""
