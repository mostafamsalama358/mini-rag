"""T061 — RecommendationTrace fields."""

from __future__ import annotations

from core.query_parser.need_frame import NeedFrame
from services.rag.recommend.constraints import seed_candidates_for_tags
from services.rag.recommend.decision import decide


def test_trace_exposes_matched_indications_and_rank() -> None:
    cands = seed_candidates_for_tags(["acidity", "ppi"])
    decision, trace = decide(
        need_frame=NeedFrame(
            normalized_need="acidity",
            indication_tags=["acidity", "ppi"],
            confidence=0.9,
            language="en",
        ),
        candidates=cands,
        language="en",
        correlation_id="req-1",
    )
    assert decision.decision_type == "recommend"
    payload = trace.to_diagnostics()
    assert payload["candidate_count"] >= 1
    assert any(c.get("matched_indications") for c in payload["candidates"])
    assert any(
        c.get("rank_contribution") is not None or c.get("score") is not None
        for c in payload["candidates"]
    )
