"""T044 — planner vignette themes present."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


def test_planner_vignette_themes() -> None:
    rows = markdown_table_rows(read(GOV_019 / "failure-vignette-catalog.md"))
    themes = " ".join(r[-1].lower() for r in rows[1:])
    assert "omitted-constraint" in themes
    assert "re-parse" in themes
