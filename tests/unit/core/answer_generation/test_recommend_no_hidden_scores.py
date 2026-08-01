"""T062 — no hidden scores required in user text."""

from __future__ import annotations

from core.answer_generation.composition.recommend_explanation_policy import (
    violates_hidden_score_policy,
)


def test_user_facing_sample_clean() -> None:
    sample = (
        "In-corpus options for acidity include Risek and Gaviscon based on leaflet indications. "
        "Consult a pharmacist if pregnant."
    )
    assert not violates_hidden_score_policy(sample)
