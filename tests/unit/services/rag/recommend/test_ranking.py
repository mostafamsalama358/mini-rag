"""T018 — ranking composition."""

from __future__ import annotations

from services.rag.recommend.models import ProductIdentity, RankingSignals, RecommendationCandidate
from services.rag.recommend.ranking import apply_ranking, compose_score


def test_compose_score_uses_policy_weights() -> None:
    score, breakdown = compose_score(
        RankingSignals(
            indication_match=1.0,
            retrieval_evidence=0.0,
            reranker_confidence=0.0,
            safety_fitness=0.0,
            formulary_preference=0.0,
        )
    )
    assert score > 0
    assert "indication_match" in breakdown


def test_apply_ranking_orders_by_score() -> None:
    c1 = RecommendationCandidate(
        candidate_id="a",
        product_identity=ProductIdentity(brand="A"),
        ranking_signals=RankingSignals(indication_match=0.2, retrieval_evidence=0.2),
    )
    c2 = RecommendationCandidate(
        candidate_id="b",
        product_identity=ProductIdentity(brand="B"),
        ranking_signals=RankingSignals(indication_match=1.0, retrieval_evidence=1.0),
    )
    ranked = apply_ranking([c1, c2])
    assert ranked[0].candidate_id == "b"
