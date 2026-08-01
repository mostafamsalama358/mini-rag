from services.FieldRegistry import FieldRegistry
from services.rag.metadata_enrichment import (
    enrich_chunk_metadata,
    extract_field_names,
    metadata_contract_ok,
)


def _pharmacy_enrichment():
    registry = FieldRegistry().load()
    return registry.build_profile("pharmacy").metadata


def test_extract_contraindications_and_pregnancy_fields():
    text = (
        "4. Do not take MediQuick Ibuprofen if\n"
        "- You are in the last 3 months of pregnancy (third trimester).\n"
    )
    rules = _pharmacy_enrichment().enrichment
    fields = extract_field_names(text, rules.field_patterns)
    assert "contraindications" in fields
    assert "pregnancy" in fields


def test_enrich_sets_entity_and_field_for_leaflet():
    text = (
        "MEDIQUICK Ibuprofen 200 mg Film-Coated Tablets\n"
        "2. Dosage — Adults and adolescents (12 years and over)\n"
        "Do not take more than 6 tablets (1200 mg) in any 24-hour period.\n"
    )
    meta = enrich_chunk_metadata(
        {"file_name": "leaflet.txt"},
        text,
        enrichment=_pharmacy_enrichment(),
    )
    assert meta.get("entity_key") == "entity"
    assert "Ibuprofen" in (meta.get("entity") or "")
    assert meta.get("field_name") == "dosage"
    assert "dosage" in (meta.get("field_names") or [])
    assert meta.get("metadata_completeness") in {"complete", "partial"}


def test_metadata_contract_strict():
    ok, reason = metadata_contract_ok({"entity": "x"}, strict=True)
    assert ok is False
    assert reason == "field_name_missing"
    ok2, _ = metadata_contract_ok(
        {"entity": "x", "field_name": "dosage"},
        strict=True,
    )
    assert ok2 is True


def test_warfarin_note_entity_and_interactions_field():
    text = (
        "NORTHBRIDGE CLINICAL NOTE — Anticoagulant Interactions\n"
        "Warfarin has a narrow therapeutic index.\n"
        "NSAIDs including ibuprofen can increase INR. Prefer lowest effective dose.\n"
    )
    meta = enrich_chunk_metadata(
        {"file_name": "northbridge_warfarin_note.txt"},
        text,
        enrichment=_pharmacy_enrichment(),
    )
    assert meta.get("entity") == "warfarin"
    assert meta.get("field_name") == "interactions"
    assert "ibuprofen" in [a.lower() for a in (meta.get("entity_aliases") or [])]


def test_generic_profile_does_not_inject_pharmacy_heuristics():
    registry = FieldRegistry().load()
    generic = registry.build_profile("generic").metadata
    text = (
        "MEDIQUICK Ibuprofen 200 mg Film-Coated Tablets\n"
        "2. Dosage — Adults and adolescents\n"
    )
    meta = enrich_chunk_metadata({"file_name": "leaflet.txt"}, text, enrichment=generic)
    assert meta.get("entity") is None
    assert meta.get("field_name") is None
