"""T032 companion — unknown ≠ safe."""

from __future__ import annotations

from services.rag.recommend.safety import evaluate_safety


def test_missing_label_unknown_not_safe() -> None:
    outcome, _, fitness = evaluate_safety(None, population="breastfeeding")
    assert outcome != "pass" or fitness < 1.0
    assert outcome in ("unknown", "demote")
