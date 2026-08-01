"""T048 — compare/explanation policy posture (contract-level)."""

from __future__ import annotations

from core.answer_generation.composition.recommend_explanation_policy import (
    RECOMMEND_COMPARE_INSTRUCTIONS,
    claims_unsupported_superiority,
)


def test_compare_instructions_forbid_hidden_scores() -> None:
    assert "hidden" in RECOMMEND_COMPARE_INSTRUCTIONS.casefold()
    assert not claims_unsupported_superiority(
        "Risek may suit PPI indication per leaflet; Gaviscon is antacid."
    )
