"""T031/T032 — safety filter."""

from __future__ import annotations

from services.rag.recommend.models import ProductIdentity, RecommendationCandidate
from services.rag.recommend.safety import apply_safety_filter, evaluate_safety


def test_pregnancy_avoid_excludes_or_demotes() -> None:
    outcome, statuses, fitness = evaluate_safety(
        {"pregnancy": "contraindicated"}, population="pregnancy"
    )
    assert outcome == "exclude"
    assert fitness == 0.0


def test_unknown_is_not_safe() -> None:
    outcome, statuses, fitness = evaluate_safety({}, population="pregnancy")
    assert outcome in ("unknown", "demote")
    assert fitness < 1.0


def test_apply_safety_filter_on_candidates() -> None:
    cands = [
        RecommendationCandidate(
            candidate_id="1",
            product_identity=ProductIdentity(brand="Brufen"),
            metadata={"safety": {"pregnancy": "avoid"}},
        )
    ]
    out = apply_safety_filter(cands, population="pregnant patient")
    assert out[0].safety_outcome in ("demote", "exclude", "unknown")
