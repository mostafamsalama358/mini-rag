"""T044 — modularity-freeze cites C8 and 016 M0."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, read


def test_modularity_freeze_cites_c8_and_m0() -> None:
    text = read(GOV_018 / "modularity-freeze.md")
    assert "C8" in text
    assert "M0" in text
    assert "016" in text
