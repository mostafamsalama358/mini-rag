"""T042 — ambiguous need clarification."""

from __future__ import annotations

from core.query_parser.parser import _try_recommend_plan


def test_ambiguous_stomach_needs_clarification() -> None:
    plan_pair = _try_recommend_plan("مشكلة في البطن", language="ar")
    assert plan_pair is not None
    plan, _ = plan_pair
    assert plan.needs_clarification is True or (
        plan.need_frame and plan.need_frame.ambiguity_group
    )
