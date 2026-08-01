"""T042 — planner metrics owned by Retrieval Planner."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


def test_planner_metrics_owned_by_planner() -> None:
    rows = markdown_table_rows(read(GOV_019 / "metric-ownership-registry.md"))
    by_metric = {r[0].strip(): r[1].strip() for r in rows[1:]}
    assert by_metric["Plan Fidelity"] == "Retrieval Planner"
    assert by_metric["Strategy Alignment"] == "Retrieval Planner"
