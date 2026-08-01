"""Unit tests for shadow overlap / first_divergent_stage helpers."""

from __future__ import annotations

from services.rag.pipeline.shadow_diagnostics import (
    answer_similarity,
    evidence_overlap,
    first_divergent_stage,
    plan_strategy_match,
    retrieval_overlap,
)


def test_retrieval_overlap_jaccard():
    assert retrieval_overlap(["a", "b"], ["b", "c"]) == 1 / 3


def test_evidence_overlap_empty():
    assert evidence_overlap([], []) == 1.0
    assert evidence_overlap(["a"], []) == 0.0


def test_answer_similarity_identical():
    assert answer_similarity("Hello", "hello") == 1.0


def test_first_divergent_stage_outcome_mismatch():
    stage = first_divergent_stage(
        legacy_outcome="success",
        unified_outcome="no_context",
        retrieval_overlap_score=0.9,
        evidence_overlap_score=0.9,
        answer_sim=0.9,
        divergence_threshold=0.85,
    )
    assert stage == "answer"


def test_first_divergent_stage_low_retrieval_overlap():
    stage = first_divergent_stage(
        legacy_outcome="success",
        unified_outcome="success",
        retrieval_overlap_score=0.2,
        evidence_overlap_score=0.9,
        answer_sim=0.95,
        divergence_threshold=0.85,
    )
    assert stage == "retrieve"


def test_plan_strategy_match_vector_path():
    assert plan_strategy_match("entity_scoped", ["dense", "sparse"]) is True
