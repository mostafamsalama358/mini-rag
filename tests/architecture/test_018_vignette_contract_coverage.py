"""T027 — every vignette cites a valid C1–C12 id from continuity index."""

from __future__ import annotations

import re

from tests.architecture._repo import GOV_018, markdown_table_rows, read


def _contract_ids(text: str) -> set[str]:
    return set(re.findall(r"C\d+", text))


def test_vignettes_cite_indexed_contracts() -> None:
    index_ids = _contract_ids(read(GOV_018 / "continuity-contract-index.md"))
    assert {f"C{i}" for i in range(1, 13)}.issubset(index_ids)

    rows = markdown_table_rows(read(GOV_018 / "failure-vignette-catalog.md"))
    for row in rows[1:]:
        cited = _contract_ids(row[2])
        assert cited, f"vignette {row[0]} has no contract id"
        assert cited <= index_ids, f"vignette {row[0]} cites unknown {cited - index_ids}"
