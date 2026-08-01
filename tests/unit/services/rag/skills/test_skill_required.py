"""US2 — missing skill_id rejected when registry non-empty."""

from __future__ import annotations

import pytest

from services.FieldRegistry import get_field_registry
from services.rag.skills import SkillResolutionError, resolve_skill


def test_pharmacy_requires_skill() -> None:
    profile = get_field_registry().build_profile("pharmacy")
    assert profile.skills
    with pytest.raises(SkillResolutionError):
        resolve_skill(profile, "")


def test_generic_allows_no_skill() -> None:
    profile = get_field_registry().build_profile("generic")
    assert resolve_skill(profile, None) is None
