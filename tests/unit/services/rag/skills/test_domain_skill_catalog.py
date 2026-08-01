"""US5 — domain-scoped Skill catalogs are isolated."""

from __future__ import annotations

from services.FieldRegistry import get_field_registry
from services.rag.skills import list_skill_catalog, resolve_skill, SkillResolutionError
import pytest


def test_pharmacy_and_legal_catalogs_differ() -> None:
    reg = get_field_registry()
    pharmacy = list_skill_catalog(reg.build_profile("pharmacy"))
    legal = list_skill_catalog(reg.build_profile("legal"))
    ph_ids = {s["id"] for s in pharmacy}
    legal_ids = {s["id"] for s in legal}
    assert "interactions" in ph_ids
    assert "interactions" not in legal_ids
    assert "clause_lookup" in legal_ids


def test_cross_domain_skill_rejected() -> None:
    legal = get_field_registry().build_profile("legal")
    with pytest.raises(SkillResolutionError):
        resolve_skill(legal, "interactions")
