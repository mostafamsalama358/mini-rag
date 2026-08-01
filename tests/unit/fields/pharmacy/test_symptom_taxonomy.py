"""T017 — symptom taxonomy mapping."""

from __future__ import annotations

from fields.pharmacy.taxonomy_mapper import TaxonomyMapper, map_need


def test_acidity_ar_maps_to_tags() -> None:
    m = map_need("دواء للحموضة؟")
    assert "acidity" in m.indication_tags or "ppi" in m.indication_tags or "antacid" in m.indication_tags
    assert m.confidence >= 0.5


def test_migraine_en_maps() -> None:
    m = map_need("medicine for migraine headache")
    assert "migraine" in m.indication_tags or "headache" in m.indication_tags


def test_many_to_many_stomach_ambiguity() -> None:
    m = TaxonomyMapper().map_query("مشكلة في البطن")
    assert m.ambiguity_group == "gi_broad" or m.confidence < 0.55
