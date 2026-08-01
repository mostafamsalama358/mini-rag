"""T057 — eight drift categories present."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


REQUIRED = {
    "Data Drift",
    "Query Drift",
    "Retrieval Drift",
    "Ranking Drift",
    "Citation Drift",
    "Answer Drift",
    "Latency Drift",
    "Cost Drift",
}


def test_drift_taxonomy_complete() -> None:
    rows = markdown_table_rows(read(GOV_019 / "drift-taxonomy-catalog.md"))
    cats = {r[0].strip() for r in rows[1:]}
    missing = sorted(REQUIRED - cats)
    assert not missing, f"Missing drift categories: {missing}"
