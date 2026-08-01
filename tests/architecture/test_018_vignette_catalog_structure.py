"""T026 — vignette catalog columns and ≥12 rows."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, markdown_table_rows, read


def test_vignette_catalog_structure() -> None:
    rows = markdown_table_rows(read(GOV_018 / "failure-vignette-catalog.md"))
    assert rows
    header = [h.lower() for h in rows[0]]
    assert "vignetteid" in header[0].replace(" ", "").lower() or "vignette" in header[0].lower()
    assert any("contract" in h.lower() for h in header)
    data = rows[1:]
    assert len(data) >= 12, f"need ≥12 vignettes, got {len(data)}"
