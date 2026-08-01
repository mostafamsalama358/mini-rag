"""T047 — explanation policy."""

from __future__ import annotations

from core.answer_generation.composition.recommend_explanation_policy import (
    claims_unsupported_superiority,
    medical_advice_disclaimer,
    sanitize_recommend_answer,
    violates_hidden_score_policy,
)


def test_hidden_score_detected() -> None:
    assert violates_hidden_score_policy("Chosen due to hidden score 0.91")


def test_superiority_detected() -> None:
    assert claims_unsupported_superiority("Risek is clinically superior to Gaviscon")


def test_sanitize_adds_disclaimer() -> None:
    out = sanitize_recommend_answer("Try Risek.", language="en")
    assert "not a medical prescription" in out.casefold() or "corpus-bounded" in out.casefold()
    assert medical_advice_disclaimer(language="en") in out or "Consult" in out
