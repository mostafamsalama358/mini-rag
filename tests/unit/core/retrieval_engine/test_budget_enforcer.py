"""Unit tests for BudgetEnforcer."""

from __future__ import annotations

from core.retrieval_engine.budget.enforcer import BudgetEnforcer
from core.retrieval_engine.models import RawCandidate, RetrievedCandidate
from core.retrieval_planner.models import RetrievalLimits


def _raw(i: int) -> RawCandidate:
    return RawCandidate(
        chunk_id=f"c{i}",
        document_id="d1",
        raw_score=1.0 - i * 0.1,
        retriever_id="dense_vector",
        strategy="semantic",
        expander_variant_id="v0",
    )


def _retrieved(i: int) -> RetrievedCandidate:
    return RetrievedCandidate(
        chunk_id=f"c{i}",
        document_id="d1",
        score=1.0 - i * 0.1,
        score_source="raw",
        rank=i + 1,
    )


def test_apply_candidate_cap():
    enforcer = BudgetEnforcer()
    caps = enforcer.apply_candidate_cap(
        [_raw(i) for i in range(10)],
        RetrievalLimits(max_evidence_units=3, max_candidates=3, scope="narrow"),
    )
    assert len(caps) == 3


def test_apply_evidence_cap():
    enforcer = BudgetEnforcer()
    caps = enforcer.apply_evidence_cap(
        [_retrieved(i) for i in range(10)],
        RetrievalLimits(max_evidence_units=2, max_candidates=10, scope="narrow"),
    )
    assert len(caps) == 2


def test_zero_budget_returns_empty():
    enforcer = BudgetEnforcer()
    # max_candidates must be >= max_evidence_units per planner validator,
    # so construct a limit with max_candidates=1 and manually truncate via enforcer
    # using a synthetic object.
    class _Limits:
        max_candidates = 0
        max_evidence_units = 0

    assert enforcer.apply_candidate_cap([_raw(0)], _Limits()) == []  # type: ignore[arg-type]
    assert enforcer.apply_evidence_cap([_retrieved(0)], _Limits()) == []  # type: ignore[arg-type]


def test_latency_check():
    enforcer = BudgetEnforcer()
    assert enforcer.check_latency_budget(100.0, 50) is True
    assert enforcer.check_latency_budget(10.0, 50) is False
    assert enforcer.check_latency_budget(100.0, None) is False
