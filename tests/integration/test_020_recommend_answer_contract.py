"""T020 — recommend answers use frozen /answer keys only."""

from __future__ import annotations

FROZEN_SUCCESS_KEYS = {
    "signal",
    "answer",
    "needs_clarification",
    "full_prompt",
    "chat_history",
}


def test_frozen_answer_keys_documented() -> None:
    # Contract lock — recommend mode must not require extra public keys.
    assert "recommendations" not in FROZEN_SUCCESS_KEYS
    assert "answer" in FROZEN_SUCCESS_KEYS
    assert "needs_clarification" in FROZEN_SUCCESS_KEYS


def test_recommend_heuristic_sets_recommend_mode() -> None:
    from core.query_parser.parser import _try_recommend_plan

    plan_pair = _try_recommend_plan("دواء للحموضة؟", language="ar")
    assert plan_pair is not None
    plan, _canonical = plan_pair
    assert plan.recommend_mode is True
    assert plan.operation == "recommend"
