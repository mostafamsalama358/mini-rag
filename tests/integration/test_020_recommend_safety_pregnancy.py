"""T033 — pregnancy-constrained recommend posture."""

from __future__ import annotations

from core.query_parser.need_frame import NeedFrame
from services.rag.recommend.constraints import seed_candidates_for_tags
from services.rag.recommend.decision import decide


def test_pregnancy_does_not_promote_contraindicated_first() -> None:
    cands = seed_candidates_for_tags(["pain", "fever"])
    decision, _trace = decide(
        need_frame=NeedFrame(
            normalized_need="pain",
            indication_tags=["pain", "fever"],
            population="pregnancy",
            confidence=0.9,
            language="en",
        ),
        candidates=cands,
        language="en",
    )
    assert decision.decision_type in ("recommend", "refuse", "limited_coverage")
    for cand in decision.ordered_candidates:
        assert cand.safety_outcome != "exclude"
