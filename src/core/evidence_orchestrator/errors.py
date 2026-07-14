"""Evidence Orchestrator error hierarchy."""

from __future__ import annotations


class EvidenceOrchestratorError(Exception):
    """Base error for all Evidence Orchestrator failures."""


class CollectionError(EvidenceOrchestratorError):
    """Collect stage failed."""


class DeduplicationError(EvidenceOrchestratorError):
    """Deduplicate stage failed."""


class ExpansionError(EvidenceOrchestratorError):
    """Expand stage failed."""


class CompressibilityScoringError(EvidenceOrchestratorError):
    """Compress-flag stage failed."""


class PrioritizationError(EvidenceOrchestratorError):
    """Prioritize stage failed."""


class PackagingError(EvidenceOrchestratorError):
    """Package stage failed."""


class EvidencePackVersionError(EvidenceOrchestratorError):
    """EvidencePack schema version is unsupported."""
