"""Unit tests for Evidence Orchestrator domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.evidence_orchestrator.config import (
    CompressibilityWeights,
    FusionWeights,
)
from core.evidence_orchestrator.models import (
    Citation,
    EvidenceItem,
    EvidenceItemSource,
    EvidencePack,
    OrchestratorTrace,
    compute_item_id,
    compute_pack_id,
)


def test_evidence_pack_is_empty_validator_consistent():
    trace = OrchestratorTrace()
    pack = EvidencePack(
        pack_id=compute_pack_id("rp_test", "2026-07-14T00:00:00Z"),
        plan_id="rp_test",
        items=[],
        is_empty=True,
        raw_candidate_count=0,
        trace=trace,
        created_at="2026-07-14T00:00:00Z",
    )
    assert pack.is_empty is True


def test_evidence_pack_is_empty_validator_inconsistent():
    citation = Citation(
        document_id="d1",
        chunk_id="c1",
        retrieval_score=0.5,
        score_source="fusion",
    )
    item = EvidenceItem(
        item_id=compute_item_id("c1", "d1"),
        doc_id="d1",
        chunk_id="c1",
        citation=citation,
        text="hello",
        relevance_score=0.5,
        sources=[EvidenceItemSource(strategy_id="semantic", raw_score=0.5)],
    )
    trace = OrchestratorTrace()
    with pytest.raises(ValidationError):
        EvidencePack(
            pack_id=compute_pack_id("rp_test", "2026-07-14T00:00:00Z"),
            plan_id="rp_test",
            items=[item],
            is_empty=True,
            raw_candidate_count=1,
            trace=trace,
            created_at="2026-07-14T00:00:00Z",
        )


def test_evidence_item_score_ranges():
    citation = Citation(
        document_id="d1",
        chunk_id="c1",
        retrieval_score=0.5,
        score_source="fusion",
    )
    with pytest.raises(ValidationError):
        EvidenceItem(
            item_id=compute_item_id("c1", "d1"),
            doc_id="d1",
            chunk_id="c1",
            citation=citation,
            text="hello",
            relevance_score=1.5,
            sources=[EvidenceItemSource(strategy_id="semantic", raw_score=0.5)],
        )
    with pytest.raises(ValidationError):
        EvidenceItem(
            item_id=compute_item_id("c1", "d1"),
            doc_id="d1",
            chunk_id="c1",
            citation=citation,
            text="hello",
            relevance_score=0.5,
            compressibility_score=-0.1,
            sources=[EvidenceItemSource(strategy_id="semantic", raw_score=0.5)],
        )


def test_citation_non_empty_strings():
    with pytest.raises(ValidationError):
        Citation(
            document_id="",
            chunk_id="c1",
            retrieval_score=0.5,
            score_source="fusion",
        )


def test_fusion_weights_sum_validator():
    FusionWeights()
    with pytest.raises(ValidationError):
        FusionWeights(retrieval=0.5, entity=0.3, recency=0.1)


def test_compressibility_weights_sum_validator():
    CompressibilityWeights()
    with pytest.raises(ValidationError):
        CompressibilityWeights(redundancy=0.5, relevance_inverse=0.3)


def test_id_prefixes():
    item_id = compute_item_id("chunk_a", "doc_b")
    pack_id = compute_pack_id("rp_x", "2026-07-14T00:00:00Z")
    assert item_id.startswith("ei_")
    assert pack_id.startswith("ep_")
    assert len(item_id) == 19
    assert len(pack_id) == 19
