"""T063 — recommend trace diagnostics."""

from __future__ import annotations

from core.query_parser.need_frame import NeedFrame
from services.rag.recommend.constraints import seed_candidates_for_tags
from services.rag.recommend.decision import decide
from services.rag.recommend.trace import RecommendationTrace


def test_recommend_trace_diagnostics_payload() -> None:
    cands = seed_candidates_for_tags(["acidity"])
    decision, trace = decide(
        need_frame=NeedFrame(
            normalized_need="acidity",
            indication_tags=["acidity"],
            confidence=0.9,
        ),
        candidates=cands,
        correlation_id="diag-1",
    )
    assert isinstance(trace, RecommendationTrace)
    payload = trace.to_diagnostics()
    assert payload["decision_type"] == decision.decision_type
    assert payload["correlation_id"] == "diag-1"
    assert payload["candidate_count"] >= 1
