"""Evidence Orchestrator — collect, deduplicate, expand, score, prioritize, package."""

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import (
    IChunkReader,
    ICompressibilityScorer,
    IDeduplicator,
    IEvidenceCollector,
    IEvidenceExpander,
    IEvidencePrioritizer,
    ITokenCounter,
)
from core.evidence_orchestrator.models import (
    Citation,
    EvidenceItem,
    EvidencePack,
)
from core.evidence_orchestrator.pipeline import EvidenceOrchestrator
from core.evidence_orchestrator.registry import EvidenceOrchestratorRegistry

__all__ = [
    "Citation",
    "EvidenceItem",
    "EvidenceOrchestrator",
    "EvidenceOrchestratorConfig",
    "EvidenceOrchestratorRegistry",
    "EvidencePack",
    "IChunkReader",
    "ICompressibilityScorer",
    "IDeduplicator",
    "IEvidenceCollector",
    "IEvidenceExpander",
    "IEvidencePrioritizer",
    "ITokenCounter",
]
