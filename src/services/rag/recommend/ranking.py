"""Recommendation Score composition — policy-owned weights."""

from __future__ import annotations

from typing import Any

from services.rag.recommend.models import RankingSignals, RecommendationCandidate
from services.rag.recommend.pack_access import load_recommendation_policy


def compose_score(
    signals: RankingSignals,
    *,
    policy: dict[str, Any] | None = None,
) -> tuple[float, dict[str, float]]:
    pol = policy or load_recommendation_policy()
    weights = dict(pol.get("signal_weights") or {})
    enabled = set(pol.get("enabled_signals") or weights.keys())

    raw = {
        "indication_match": signals.indication_match,
        "retrieval_evidence": signals.retrieval_evidence,
        "reranker_confidence": signals.reranker_confidence,
        "safety_fitness": signals.safety_fitness,
        "formulary_preference": signals.formulary_preference,
    }
    breakdown: dict[str, float] = {}
    total_w = 0.0
    score = 0.0
    for name, value in raw.items():
        if name not in enabled or value is None:
            continue
        w = float(weights.get(name, 0.0))
        if w <= 0:
            continue
        contrib = w * float(value)
        breakdown[name] = contrib
        score += contrib
        total_w += w
    if total_w > 0:
        score = score / total_w
    return score, breakdown


def apply_ranking(
    candidates: list[RecommendationCandidate],
    *,
    policy: dict[str, Any] | None = None,
) -> list[RecommendationCandidate]:
    pol = policy or load_recommendation_policy()
    scored: list[RecommendationCandidate] = []
    for cand in candidates:
        score, breakdown = compose_score(cand.ranking_signals, policy=pol)
        scored.append(
            cand.model_copy(
                update={
                    "recommendation_score": score,
                    "signal_breakdown": breakdown,
                }
            )
        )
    scored.sort(key=lambda c: c.recommendation_score, reverse=True)

    if pol.get("prefer_safer_candidate"):
        # Stable re-order: among close scores, prefer higher safety_fitness
        scored.sort(
            key=lambda c: (
                c.recommendation_score,
                float(c.ranking_signals.safety_fitness or 0.0),
            ),
            reverse=True,
        )
    return scored
