"""T040 — taxonomy ambiguity."""

from __future__ import annotations

from fields.pharmacy.taxonomy_mapper import map_need


def test_cold_ambiguity_group() -> None:
    m = map_need("I have a cold")
    assert m.ambiguity_group == "cold_broad" or "cold" in m.indication_tags
