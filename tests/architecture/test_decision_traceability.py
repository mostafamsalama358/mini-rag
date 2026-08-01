"""T018 — Architecture Decisions map to ADR or Principle/Invariant."""

from __future__ import annotations

import re

from tests.architecture._repo import GOV, SPEC, read


def test_d1_to_d4_listed_in_adr_index() -> None:
    index = read(GOV / "adr-index.md")
    for decision, adr in (
        ("D1", "ADR-001"),
        ("D2", "ADR-002"),
        ("D3", "ADR-003"),
        ("D4", "ADR-004"),
    ):
        assert decision in index, f"{decision} missing from adr-index.md"
        assert adr in index, f"{adr} missing from adr-index.md"


def test_spec_lists_adr_001_through_004() -> None:
    spec = read(SPEC)
    for adr in ("ADR-001", "ADR-002", "ADR-003", "ADR-004"):
        assert adr in spec


def test_standing_decisions_have_non_adr_authority() -> None:
    index = read(GOV / "adr-index.md")
    assert "D5" in index
    assert re.search(r"D5.*I11|Principle", index, flags=re.I | re.S)
