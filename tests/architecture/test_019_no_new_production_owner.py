"""T018 — primary owners map to allowed parties; no Quality/Evaluation traffic owner."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


ALLOWED_OWNERS = {
    "Retrieval Engine",
    "Retrieval Planner",
    "Answer Generation",
    "Whole Pipeline (ops attribution)",
    "Query Understanding",
    "Evidence",
    "Context",
    "Context Builder",
    "Evaluation system",
}


def test_no_new_production_owner() -> None:
    rows = markdown_table_rows(read(GOV_019 / "metric-ownership-registry.md"))
    data = rows[1:]
    owners = {row[1].strip() for row in data}
    assert "Quality Owner" not in owners
    assert "Quality" not in owners
    # "Evaluation" alone as traffic owner is forbidden; ops attribution and Evaluation system ok
    unexpected = sorted(owners - ALLOWED_OWNERS)
    assert not unexpected, f"Unexpected primary owners: {unexpected}"
