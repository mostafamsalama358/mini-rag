"""T053 — recommend metric catalog completeness."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT, read

CATALOG = (
    REPO_ROOT
    / "specs"
    / "020-pharmacy-recommendation"
    / "governance"
    / "recommend-metric-catalog.md"
)

REQUIRED = [
    "Recall@K",
    "Precision@K",
    "MRR",
    "nDCG",
    "Safety Precision",
    "Safety Recall",
    "False Recommendation Rate",
    "Clarification Rate",
    "Corpus-Boundedness",
    "Recommendation Diversity",
]


def test_recommend_metric_catalog_complete() -> None:
    text = read(CATALOG)
    missing = [m for m in REQUIRED if m not in text]
    assert not missing, f"Missing metrics: {missing}"
    assert "019" in text
