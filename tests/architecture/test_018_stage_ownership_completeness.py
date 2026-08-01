"""T017 — every ownership-map concern has primary owner + spec section + contract id."""

from __future__ import annotations

import re

from tests.architecture._repo import GOV_018, markdown_table_rows, read


def test_stage_ownership_rows_complete() -> None:
    rows = markdown_table_rows(read(GOV_018 / "stage-ownership-map.md"))
    assert rows, "stage-ownership-map.md has no table"
    header = [h.lower() for h in rows[0]]
    assert "concern" in header[0]
    data = rows[1:]
    assert len(data) >= 20, f"expected many concerns, got {len(data)}"
    for row in data:
        concern, owner, _secondary, section, contracts = row[:5]
        assert concern.strip(), "empty concern"
        assert owner.strip(), f"missing primary owner for {concern}"
        assert re.search(r"§|C\d+", section) or section.strip().startswith("C"), (
            f"missing spec section for {concern}: {section}"
        )
        assert re.search(r"C\d+", contracts) or contracts.strip() == "—", (
            f"missing contract ids for {concern}: {contracts}"
        )
