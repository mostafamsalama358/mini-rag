"""T045 — compatibility contract covers 014–017; relationship doc references it."""

from __future__ import annotations

from tests.architecture._repo import CONTRACTS_018, GOV_018, read


def test_compatibility_covers_014_017() -> None:
    contract = read(CONTRACTS_018 / "compatibility.md")
    for feat in ("014", "015", "016", "017"):
        assert feat in contract
    rel = read(GOV_018 / "relationship-to-014-017.md")
    assert "compatibility.md" in rel
    for feat in ("014", "015", "016", "017"):
        assert feat in rel
