"""Unit tests for Skill-bound entity pair heuristics (interactions)."""

from __future__ import annotations

from services.rag.skills.entity_parse import _heuristic_entities


def test_arabic_wa_pair_with_parentheses_extracts_two_drugs():
    query = "هل في تفاعل بين (Congestal )و (Warfarin)؟"
    found = _heuristic_entities(
        query,
        catalog_terms=["Congestal", "Panadol"],
        fingerprint_index=None,
        min_score=0.5,
        entity_aliases=None,
    )
    upper = {e.upper() for e in found}
    assert "CONGESTAL" in upper
    assert "WARFARIN" in upper


def test_english_with_pair_still_works():
    query = "Does Congestal interact with Warfarin?"
    found = _heuristic_entities(
        query,
        catalog_terms=["Congestal"],
        fingerprint_index=None,
        min_score=0.5,
        entity_aliases=None,
    )
    upper = {e.upper() for e in found}
    assert "CONGESTAL" in upper
    assert "WARFARIN" in upper
