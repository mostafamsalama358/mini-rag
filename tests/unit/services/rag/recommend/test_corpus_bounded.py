"""T019 — corpus-boundedness."""

from __future__ import annotations

from services.rag.recommend.models import ProductIdentity, RecommendationCandidate
from services.rag.recommend.policy import filter_out_of_corpus, is_in_corpus


def test_is_in_corpus() -> None:
    assert is_in_corpus("Risek", {"risek", "gaviscon"})
    assert not is_in_corpus("InventedDrug", {"risek"})


def test_filter_out_of_corpus() -> None:
    cands = [
        RecommendationCandidate(
            candidate_id="1",
            product_identity=ProductIdentity(brand="Risek", product_line="Risek"),
            in_corpus=True,
        ),
        RecommendationCandidate(
            candidate_id="2",
            product_identity=ProductIdentity(brand="FakeMed", product_line="FakeMed"),
            in_corpus=True,
        ),
    ]
    kept = filter_out_of_corpus(cands, corpus_ids={"Risek"})
    assert len(kept) == 1
    assert kept[0].product_identity.brand == "Risek"
