"""Shared fixtures for Context Builder unit tests."""

from __future__ import annotations

from core.context_builder.config import BudgetReservations, ContextBuilderConfig
from core.evidence_orchestrator.models import (
    Citation,
    EvidenceItem,
    EvidenceItemSource,
    EvidencePack,
    OrchestratorTrace,
    compute_item_id,
    compute_pack_id,
)
import pytest


def _citation(**kwargs) -> Citation:
    defaults = {
        "document_id": "doc1",
        "chunk_id": "chunk1",
        "retrieval_score": 0.8,
        "score_source": "fusion",
    }
    defaults.update(kwargs)
    return Citation(**defaults)


def make_item(
    *,
    item_id: str | None = None,
    doc_id: str = "doc1",
    chunk_id: str = "chunk1",
    text: str = "Sample evidence text.",
    relevance_score: float = 0.8,
    compressibility_score: float = 0.0,
    entity_tags: list[str] | None = None,
    section_path: list[str] | None = None,
) -> EvidenceItem:
    chunk_id = chunk_id or "chunk1"
    return EvidenceItem(
        item_id=item_id or compute_item_id(chunk_id, doc_id),
        doc_id=doc_id,
        chunk_id=chunk_id,
        section_path=section_path or [],
        entity_tags=entity_tags or [],
        citation=_citation(document_id=doc_id, chunk_id=chunk_id),
        text=text,
        relevance_score=relevance_score,
        compressibility_score=compressibility_score,
        sources=[EvidenceItemSource(strategy_id="semantic", raw_score=relevance_score)],
    )


def make_pack(items: list[EvidenceItem], *, plan_id: str = "rp_test") -> EvidencePack:
    created_at = "2026-07-14T12:00:00Z"
    return EvidencePack(
        pack_id=compute_pack_id(plan_id, created_at),
        plan_id=plan_id,
        items=items,
        is_empty=len(items) == 0,
        raw_candidate_count=len(items),
        trace=OrchestratorTrace(),
        created_at=created_at,
    )


def make_empty_pack(*, plan_id: str = "rp_test") -> EvidencePack:
    return make_pack([], plan_id=plan_id)


def build_synthetic_pack(
    *,
    n_items: int = 20,
    tokens_per_item: int = 600,
    relevance_start: float = 1.0,
    relevance_step: float = 0.01,
) -> EvidencePack:
    char_len = max(4, tokens_per_item * 4)
    items = []
    for i in range(n_items):
        text = f"Evidence item {i}. " + ("x" * (char_len - 20))
        items.append(
            make_item(
                chunk_id=f"chunk_{i}",
                text=text,
                relevance_score=max(0.0, relevance_start - (i * relevance_step)),
                compressibility_score=0.1,
            )
        )
    return make_pack(items)


def build_pack_with_mix(
    *,
    high_compress_count: int,
    high_score: float,
    low_compress_count: int,
    low_score: float,
    tokens_per_item: int,
) -> EvidencePack:
    char_len = max(4, tokens_per_item * 4)
    items: list[EvidenceItem] = []
    for i in range(high_compress_count):
        text = f"High compress {i}. " + ("h" * (char_len - 20))
        items.append(
            make_item(
                chunk_id=f"high_{i}",
                text=text,
                relevance_score=0.5 + (i * 0.01),
                compressibility_score=high_score,
            )
        )
    for i in range(low_compress_count):
        text = f"Low compress {i}. " + ("l" * (char_len - 20))
        items.append(
            make_item(
                chunk_id=f"low_{i}",
                text=text,
                relevance_score=0.95 - (i * 0.01),
                compressibility_score=low_score,
            )
        )
    items.sort(key=lambda item: item.relevance_score, reverse=True)
    return make_pack(items)


@pytest.fixture
def default_config() -> ContextBuilderConfig:
    return ContextBuilderConfig(
        total_context_window=8000,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
        compression_enabled=True,
        compressibility_threshold=0.7,
        final_dedup_enabled=True,
    )
