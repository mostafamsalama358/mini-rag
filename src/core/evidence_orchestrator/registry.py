"""Registry wiring concrete Evidence Orchestrator stage implementations."""

from __future__ import annotations

from core.chunking.models import Chunk
from core.evidence_orchestrator.collection.retrieval_result_collector import (
    RetrievalResultCollector,
)
from core.evidence_orchestrator.compression.redundancy_scorer import RedundancyScorer
from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.deduplication.embedding_deduplicator import (
    EmbeddingDeduplicator,
)
from core.evidence_orchestrator.expansion.lineage_expander import LineageExpander
from core.evidence_orchestrator.interfaces import (
    IChunkReader,
    ICompressibilityScorer,
    IDeduplicator,
    IEmbeddingProvider,
    IEvidenceCollector,
    IEvidenceExpander,
    IEvidencePrioritizer,
    ITokenCounter,
)
from core.evidence_orchestrator.packaging.pack_assembler import PackAssembler
from core.evidence_orchestrator.pipeline import EvidenceOrchestrator
from core.evidence_orchestrator.prioritization.fusion_prioritizer import (
    FusionPrioritizer,
)
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)


class NoOpChunkReader(IChunkReader):
    """Stub chunk reader for tests or when expansion is disabled."""

    async def get_chunk(self, chunk_id: str, document_id: str) -> Chunk | None:
        return None


class EvidenceOrchestratorRegistry:
    def __init__(
        self,
        *,
        collector: IEvidenceCollector | None = None,
        deduplicator: IDeduplicator | None = None,
        expander: IEvidenceExpander | None = None,
        compressibility_scorer: ICompressibilityScorer | None = None,
        prioritizer: IEvidencePrioritizer | None = None,
        chunk_reader: IChunkReader | None = None,
        token_counter: ITokenCounter | None = None,
        embedding_provider: IEmbeddingProvider | None = None,
    ) -> None:
        counter = token_counter or CharacterApproximationTokenCounter()
        self._collector = collector or RetrievalResultCollector(token_counter=counter)
        self._deduplicator = deduplicator or EmbeddingDeduplicator(
            embedding_provider=embedding_provider
        )
        self._expander = expander or LineageExpander()
        self._compressibility_scorer = (
            compressibility_scorer or RedundancyScorer()
        )
        self._prioritizer = prioritizer or FusionPrioritizer()
        self._chunk_reader = chunk_reader or NoOpChunkReader()
        self._token_counter = counter
        self._pack_assembler = PackAssembler(token_counter=counter)

    def build_orchestrator(
        self,
        config: EvidenceOrchestratorConfig | None = None,
    ) -> EvidenceOrchestrator:
        _ = config  # reserved for future config-driven wiring
        return EvidenceOrchestrator(
            collector=self._collector,
            deduplicator=self._deduplicator,
            expander=self._expander,
            compressibility_scorer=self._compressibility_scorer,
            prioritizer=self._prioritizer,
            pack_assembler=self._pack_assembler,
            chunk_reader=self._chunk_reader,
            token_counter=self._token_counter,
        )
