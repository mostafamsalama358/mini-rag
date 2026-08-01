"""T059 — monitoring views present."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


REQUIRED = {
    "Quality Health",
    "Retrieval Health",
    "Planner Health",
    "Ops Health",
    "Gate Status",
    "Defect Hotspots",
    "Drift Board",
    "Experiment Board",
}


def test_monitoring_views_present() -> None:
    rows = markdown_table_rows(read(GOV_019 / "monitoring-view-index.md"))
    views = {r[0].strip() for r in rows[1:]}
    missing = sorted(REQUIRED - views)
    assert not missing, f"Missing monitoring views: {missing}"
