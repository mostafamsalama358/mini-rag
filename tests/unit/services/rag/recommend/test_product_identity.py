"""T068 — product identity collapse."""

from __future__ import annotations

from services.rag.recommend.identity import collapse_package_variants
from services.rag.recommend.models import ProductIdentity, RecommendationCandidate


def test_collapse_package_only_variants() -> None:
    cands = [
        RecommendationCandidate(
            candidate_id="1",
            product_identity=ProductIdentity(
                brand="Panadol", product_line="Panadol", package="12 tabs"
            ),
        ),
        RecommendationCandidate(
            candidate_id="2",
            product_identity=ProductIdentity(
                brand="Panadol", product_line="Panadol", package="24 tabs"
            ),
        ),
        RecommendationCandidate(
            candidate_id="3",
            product_identity=ProductIdentity(
                brand="Panadol", product_line="Panadol Migraine", package="10 tabs"
            ),
        ),
    ]
    out = collapse_package_variants(cands)
    assert len(out) == 2
