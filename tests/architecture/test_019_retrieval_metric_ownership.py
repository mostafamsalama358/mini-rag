"""T027 — IR metrics owned by Retrieval Engine."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


def test_retrieval_metrics_owned_by_engine() -> None:
    rows = markdown_table_rows(read(GOV_019 / "metric-ownership-registry.md"))
    by_metric = {r[0].strip(): r[1].strip() for r in rows[1:]}
    for metric in ("Recall", "Precision", "MRR", "NDCG"):
        assert by_metric[metric] == "Retrieval Engine"
