"""T018 — primary owners must be 016 logical parties; no Quality Owner."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, markdown_table_rows, read


ALLOWED_OWNERS = {
    "Query Understanding",
    "Retrieval Plan",
    "Retrieval",
    "Evidence",
    "Context",
    "Answer Generation",
    "Offline Evaluation",
    "Composition",
    "Domain Packs",
}


def test_no_quality_owner_and_owners_are_canonical() -> None:
    rows = markdown_table_rows(read(GOV_018 / "stage-ownership-map.md"))
    data = rows[1:]
    owners = {row[1].strip() for row in data}
    assert "Quality Owner" not in owners
    assert "Quality" not in owners
    unexpected = sorted(owners - ALLOWED_OWNERS)
    assert not unexpected, f"Unexpected primary owners: {unexpected}"
