"""Candidate constraints from NeedFrame + indication seed catalog."""

from __future__ import annotations

from typing import Any

from services.rag.recommend.identity import identity_from_product_row
from services.rag.recommend.pack_access import load_indication_tags
from services.rag.recommend.models import RankingSignals, RecommendationCandidate


def seed_candidates_for_tags(
    indication_tags: list[str],
    *,
    catalog: dict[str, Any] | None = None,
) -> list[RecommendationCandidate]:
    cat = catalog or load_indication_tags()
    need = {t.casefold() for t in indication_tags if t}
    out: list[RecommendationCandidate] = []
    for idx, row in enumerate(cat.get("product_tags") or []):
        row_tags = [str(t) for t in (row.get("tags") or [])]
        overlap = [t for t in row_tags if t.casefold() in need]
        if not overlap and need:
            continue
        ident = identity_from_product_row(row)
        match_strength = len(overlap) / max(1, len(need)) if need else 0.0
        cid = f"{ident.brand}:{ident.product_line or ident.brand}:{idx}"
        out.append(
            RecommendationCandidate(
                candidate_id=cid,
                product_identity=ident,
                matched_indications=overlap or row_tags,
                evidence_pointers=[f"pack:indication_tags:{cid}"],
                ranking_signals=RankingSignals(
                    indication_match=match_strength,
                    retrieval_evidence=0.4,
                    reranker_confidence=None,
                    safety_fitness=None,
                    formulary_preference=0.0,
                ),
                in_corpus=True,
                metadata={"safety": dict(row.get("safety") or {})},
            )
        )
    return out


def merge_retrieval_evidence(
    candidates: list[RecommendationCandidate],
    *,
    evidence_by_brand: dict[str, float],
) -> list[RecommendationCandidate]:
    out: list[RecommendationCandidate] = []
    for cand in candidates:
        brand = cand.product_identity.brand.casefold()
        line = (cand.product_identity.product_line or "").casefold()
        ev = evidence_by_brand.get(line) or evidence_by_brand.get(brand)
        if ev is None:
            out.append(cand)
            continue
        signals = cand.ranking_signals.model_copy(
            update={"retrieval_evidence": float(ev)}
        )
        pointers = list(cand.evidence_pointers)
        pointers.append(f"retrieval:{brand}")
        out.append(
            cand.model_copy(
                update={"ranking_signals": signals, "evidence_pointers": pointers}
            )
        )
    return out


def metadata_filter_for_tags(indication_tags: list[str]) -> dict[str, Any]:
    """Soft constraint payload for retrieval metadata (sole path)."""
    tags = [t for t in indication_tags if t]
    if not tags:
        return {}
    return {"indication_tags_any": tags, "recommend_mode": True}
