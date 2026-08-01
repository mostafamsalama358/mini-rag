"""Recommendation Policy enforcement (bounds, corpus-boundedness)."""

from __future__ import annotations

from typing import Any

from services.rag.recommend.models import RecommendationCandidate
from services.rag.recommend.pack_access import load_recommendation_policy


def is_in_corpus(product_id: str, corpus_ids: set[str]) -> bool:
    pid = (product_id or "").strip().casefold()
    if not pid:
        return False
    normalized = {c.strip().casefold() for c in corpus_ids if c}
    return pid in normalized


def filter_out_of_corpus(
    candidates: list[RecommendationCandidate],
    *,
    corpus_ids: set[str] | None,
    policy: dict[str, Any] | None = None,
) -> list[RecommendationCandidate]:
    pol = policy or load_recommendation_policy()
    if not pol.get("never_out_of_corpus", True):
        return candidates
    if corpus_ids is None:
        # Trust candidate.in_corpus flag when no explicit set
        return [c for c in candidates if c.in_corpus]
    kept: list[RecommendationCandidate] = []
    for cand in candidates:
        key = cand.product_identity.product_line or cand.product_identity.brand
        ok = is_in_corpus(key, corpus_ids) or is_in_corpus(
            cand.product_identity.brand, corpus_ids
        )
        if ok:
            kept.append(cand.model_copy(update={"in_corpus": True}))
    return kept


def apply_count_bounds(
    candidates: list[RecommendationCandidate],
    *,
    policy: dict[str, Any] | None = None,
) -> tuple[list[RecommendationCandidate], dict[str, Any]]:
    pol = policy or load_recommendation_policy()
    max_n = int(pol.get("max_recommendations") or 3)
    min_n = int(pol.get("min_recommendations") or 0)
    bounded = candidates[: max(0, max_n)]
    for i, cand in enumerate(bounded):
        bounded[i] = cand.model_copy(update={"retained": True})
    meta = {
        "max_recommendations": max_n,
        "min_recommendations": min_n,
        "retained_count": len(bounded),
        "below_minimum": len(bounded) < min_n,
    }
    return bounded, meta


def clarification_threshold(policy: dict[str, Any] | None = None) -> float:
    pol = policy or load_recommendation_policy()
    return float(pol.get("clarification_confidence_threshold") or 0.55)
