"""T017 — every canonical metric has exactly one primary owner + contract ref."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


CANONICAL = {
    "Recall",
    "Precision",
    "MRR",
    "NDCG",
    "Plan Fidelity",
    "Strategy Alignment",
    "Faithfulness",
    "Groundedness",
    "Completeness",
    "Citation Accuracy",
    "Hallucination Rate",
    "Latency",
    "Cost",
}


def test_metric_ownership_rows_complete() -> None:
    rows = markdown_table_rows(read(GOV_019 / "metric-ownership-registry.md"))
    assert rows, "metric-ownership-registry.md has no table"
    header = [h.lower() for h in rows[0]]
    assert "metric" in header[0]
    data = rows[1:]
    metrics = {row[0].strip() for row in data}
    missing = sorted(CANONICAL - metrics)
    assert not missing, f"Missing metrics: {missing}"
    for row in data:
        metric, owner, _support, _blocking, _scope, contract = row[:6]
        assert metric.strip()
        assert owner.strip(), f"missing primary owner for {metric}"
        assert "metric-system" in contract.lower() or contract.strip(), (
            f"missing contract ref for {metric}: {contract}"
        )
