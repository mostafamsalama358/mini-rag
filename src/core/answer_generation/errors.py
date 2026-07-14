"""Answer Generation error hierarchy."""

from __future__ import annotations


class AnswerGenerationError(Exception):
    """Base error for all Answer Generation failures."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class SchemaVersionError(AnswerGenerationError):
    """Context schema version is unsupported."""


class CitationResolutionError(AnswerGenerationError):
    """Citation map lookup failed unexpectedly."""
