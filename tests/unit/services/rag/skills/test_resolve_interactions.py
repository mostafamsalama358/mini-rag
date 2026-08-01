"""US1 — resolve Interactions skill + profile filters."""

from __future__ import annotations

import pytest

from services.FieldRegistry import get_field_registry
from services.rag.skills import SkillResolutionError, resolve_skill


def test_resolve_interactions_skill() -> None:
    reg = get_field_registry()
    reg.load()
    profile = reg.build_profile("pharmacy")
    assert "interactions" in profile.skills
    binding = resolve_skill(profile, "interactions")
    assert binding is not None
    assert binding.skill_id == "interactions"
    assert binding.profile.id == "drug_interactions"
    assert "interactions" in (binding.metadata_filters.get("field") or [])


def test_missing_skill_required() -> None:
    reg = get_field_registry()
    reg.load()
    profile = reg.build_profile("pharmacy")
    with pytest.raises(SkillResolutionError) as ei:
        resolve_skill(profile, None)
    assert ei.value.code == "skill_required"
