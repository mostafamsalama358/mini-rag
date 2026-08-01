"""US1 — missing skill_id clarify/reject (022 wrapper over 021 behavior)."""

from __future__ import annotations

import pytest

from services.FieldRegistry import get_field_registry
from services.rag.skills import SkillResolutionError, resolve_skill


def test_missing_skill_required_for_pharmacy() -> None:
    reg = get_field_registry()
    reg.load()
    profile = reg.build_profile("pharmacy")
    with pytest.raises(SkillResolutionError) as ei:
        resolve_skill(profile, None)
    assert ei.value.code == "skill_required"


def test_unknown_skill_rejected() -> None:
    reg = get_field_registry()
    reg.load()
    profile = reg.build_profile("pharmacy")
    with pytest.raises(SkillResolutionError) as ei:
        resolve_skill(profile, "not_a_real_skill")
    assert ei.value.code == "unknown_skill"
