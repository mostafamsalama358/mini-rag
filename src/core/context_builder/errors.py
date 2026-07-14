"""Context Builder error hierarchy."""

from __future__ import annotations


class ContextBuildError(Exception):
    """Base error for all Context Builder failures."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class EvidencePackVersionError(ContextBuildError):
    """EvidencePack schema version is unsupported."""


class EmptyBudgetError(ContextBuildError):
    """Available token budget is zero after reservations."""


class CitationIntegrityError(ContextBuildError):
    """Citation map does not match ordered blocks."""
