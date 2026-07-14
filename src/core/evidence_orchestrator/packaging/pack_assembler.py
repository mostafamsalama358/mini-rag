"""Package stage — assemble EvidencePack from processed items."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import (
    Citation,
    CollectedItem,
    EvidenceItem,
    EvidencePack,
    OrchestratorTrace,
    compute_item_id,
    compute_pack_id,
)
from core.evidence_orchestrator.text_similarity import clamp
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from core.retrieval_engine.models import RetrievalResult
from core.retrieval_planner.models import RetrievalPlan

logger = logging.getLogger(__name__)


class PackAssembler:
    def __init__(self, token_counter: ITokenCounter | None = None) -> None:
        self._token_counter = token_counter or CharacterApproximationTokenCounter()

    def collected_to_evidence_items(
        self, collected: list[CollectedItem]
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for entry in collected:
            candidate = entry.candidate
            text = entry.effective_text
            if not text.strip():
                text = candidate.content_excerpt or " "
            citation = _build_citation(candidate)
            items.append(
                EvidenceItem(
                    item_id=compute_item_id(candidate.chunk_id, candidate.document_id),
                    doc_id=candidate.document_id,
                    chunk_id=candidate.chunk_id,
                    section_path=_section_path(candidate),
                    citation=citation,
                    text=text,
                    relevance_score=clamp(float(candidate.score)),
                    compressibility_score=0.0,
                    sources=list(entry.contributing_sources),
                    expanded=entry.expanded,
                )
            )
        return items

    def assemble(
        self,
        *,
        items: list[EvidenceItem],
        result: RetrievalResult,
        plan: RetrievalPlan,
        trace: OrchestratorTrace,
        raw_input_token_count: int,
        created_at: str | None = None,
    ) -> EvidencePack:
        timestamp = created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        pack_tokens = sum(self._token_counter.count_tokens(item.text) for item in items)
        ratio: float | None = None
        if raw_input_token_count > 0:
            ratio = clamp(pack_tokens / raw_input_token_count)

        pack = EvidencePack(
            pack_id=compute_pack_id(plan.metadata.plan_id, timestamp),
            plan_id=plan.metadata.plan_id,
            items=items,
            is_empty=len(items) == 0,
            strategies_used=list(result.metadata.executed_strategies),
            token_reduction_ratio=ratio,
            raw_candidate_count=len(result.candidates),
            trace=trace,
            created_at=timestamp,
        )
        logger.info(
            "stage=package plan_id=%s item_count=%d raw_candidate_count=%d "
            "token_reduction_ratio=%s",
            plan.metadata.plan_id,
            len(items),
            len(result.candidates),
            ratio,
        )
        return pack


def _build_citation(candidate) -> Citation:
    ref = candidate.source_ref
    return Citation(
        document_id=candidate.document_id,
        chunk_id=candidate.chunk_id,
        retrieval_score=float(candidate.score),
        score_source=candidate.score_source,
        page_number=ref.page_number if ref else None,
        section_title=ref.section_title if ref else None,
        document_title=ref.document_title if ref else None,
        chunk_index=ref.chunk_index if ref else None,
    )


def _section_path(candidate) -> list[str]:
    ref = candidate.source_ref
    if ref and ref.section_title:
        return [ref.section_title]
    return []
