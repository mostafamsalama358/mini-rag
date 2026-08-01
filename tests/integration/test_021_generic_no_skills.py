"""Polish — generic domain remains backward-compatible without skill_id."""

from __future__ import annotations

from services.FieldRegistry import get_field_registry
from services.rag.skills import resolve_skill


def test_generic_no_skills_optional() -> None:
    profile = get_field_registry().build_profile("generic")
    assert not profile.skills
    assert resolve_skill(profile, None) is None
