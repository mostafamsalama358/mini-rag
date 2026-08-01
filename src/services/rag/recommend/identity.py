"""Product Identity Rules — Brand → Line → Strength → Package."""

from __future__ import annotations

from typing import Any

from services.rag.recommend.models import ProductIdentity, RecommendationCandidate
from services.rag.recommend.pack_access import load_recommendation_policy


def identity_from_product_row(row: dict[str, Any]) -> ProductIdentity:
    brand = str(row.get("brand") or row.get("product") or "").strip()
    line = str(row.get("product_line") or brand).strip() or None
    strength = str(row.get("strength") or "").strip() or None
    package = str(row.get("package") or "").strip() or None
    level = "line"
    if package and not strength:
        level = "package"
    if strength:
        level = "strength"
    if line and line.casefold() != (brand or "").casefold():
        level = "line"
    elif brand and not line:
        level = "brand"
    return ProductIdentity(
        brand=brand or "unknown",
        product_line=line,
        strength=strength,
        package=package,
        inn=str(row.get("inn") or "").strip() or None,
        identity_level=level,  # type: ignore[arg-type]
    )


def collapse_package_variants(
    candidates: list[RecommendationCandidate],
    *,
    policy: dict[str, Any] | None = None,
) -> list[RecommendationCandidate]:
    pol = policy or load_recommendation_policy()
    rules = pol.get("identity_presentation") or {}
    if not rules.get("collapse_package_only_variants", True):
        return candidates

    seen: set[str] = set()
    out: list[RecommendationCandidate] = []
    for cand in candidates:
        ident = cand.product_identity
        # Key by brand+line (+strength if present); ignore package-only distinction
        key = "|".join(
            [
                ident.brand.casefold(),
                (ident.product_line or "").casefold(),
                (ident.strength or "").casefold(),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(cand)
    return out


def prefer_need_specific_line(
    candidates: list[RecommendationCandidate],
    *,
    need_tags: list[str],
) -> list[RecommendationCandidate]:
    if not need_tags:
        return candidates
    need = {t.casefold() for t in need_tags}

    def score(c: RecommendationCandidate) -> tuple[int, float]:
        overlap = len(need.intersection({t.casefold() for t in c.matched_indications}))
        return (overlap, c.recommendation_score)

    return sorted(candidates, key=score, reverse=True)
