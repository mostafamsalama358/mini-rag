"""T035 — SC-001…SC-010 appear in stakeholder-outcomes with validation method."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, SPEC_018, markdown_table_rows, read


def test_success_criteria_traced() -> None:
    spec = read(SPEC_018)
    for i in range(1, 11):
        assert f"SC-{i:03d}" in spec

    rows = markdown_table_rows(read(GOV_018 / "stakeholder-outcomes.md"))
    sc_cells = {row[0].strip() for row in rows[1:]}
    for i in range(1, 11):
        key = f"SC-{i:03d}"
        assert key in sc_cells, f"{key} missing from stakeholder-outcomes.md"
        row = next(r for r in rows[1:] if r[0].strip() == key)
        assert len(row) >= 3 and row[2].strip(), f"{key} missing validation method"
