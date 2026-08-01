"""T014 — governance artifact presence."""

from __future__ import annotations

from tests.architecture._repo import GOV, markdown_table_rows, read


REQUIRED_FILES = [
    "README.md",
    "ownership-registry.md",
    "lifecycle-registry.md",
    "contract-role-catalog.md",
    "capability-cards.md",
    "adr-index.md",
    "m0-freeze.md",
    "migration-runbook.md",
]


def test_governance_files_exist() -> None:
    missing = [name for name in REQUIRED_FILES if not (GOV / name).is_file()]
    assert not missing, f"Missing governance files: {missing}"


def test_ownership_registry_has_data_rows() -> None:
    rows = markdown_table_rows(read(GOV / "ownership-registry.md"))
    assert rows, "ownership-registry.md has no table"
    header = rows[0]
    assert "concern_id" in header[0] or "concern_id" in header
    data = rows[1:]
    assert len(data) >= 5, "ownership registry stub not filled"
