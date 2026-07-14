"""Evidence Orchestrator pluggable interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from core.chunking.models import Chunk
from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.models import CollectedItem, EvidenceItem
from core.retrieval_engine.models import RetrievalResult
from core.retrieval_planner.models import RetrievalPlan


class IEvidenceCollector(ABC):
    @abstractmethod
    async def collect(
        self,
        result: RetrievalResult,
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]: ...


class IDeduplicator(ABC):
    @abstractmethod
    async def deduplicate(
        self,
        items: list[CollectedItem],
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]: ...


class IChunkReader(ABC):
    @abstractmethod
    async def get_chunk(
        self,
        chunk_id: str,
        document_id: str,
    ) -> Chunk | None: ...


class IEvidenceExpander(ABC):
    @abstractmethod
    async def expand(
        self,
        items: list[CollectedItem],
        chunk_reader: IChunkReader,
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]: ...


class ICompressibilityScorer(ABC):
    @abstractmethod
    async def score(
        self,
        items: list[EvidenceItem],
        config: EvidenceOrchestratorConfig,
    ) -> list[EvidenceItem]: ...


class IEvidencePrioritizer(ABC):
    @abstractmethod
    async def prioritize(
        self,
        items: list[EvidenceItem],
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> list[EvidenceItem]: ...


class ITokenCounter(ABC):
    @abstractmethod
    def count_tokens(self, text: str) -> int: ...


@runtime_checkable
class IEmbeddingProvider(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
