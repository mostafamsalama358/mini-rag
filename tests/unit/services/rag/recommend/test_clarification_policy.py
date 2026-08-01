"""T041 — clarification policy threshold."""

from __future__ import annotations

from core.query_parser.need_frame import NeedFrame
from services.rag.recommend.decision import decide
from services.rag.recommend.policy import clarification_threshold


def test_low_confidence_clarifies() -> None:
    thr = clarification_threshold()
    decision, _trace = decide(
        need_frame=NeedFrame(confidence=max(0.0, thr - 0.2), language="en"),
        candidates=[],
        language="en",
    )
    assert decision.decision_type == "clarify"
    assert decision.clarification_prompt
