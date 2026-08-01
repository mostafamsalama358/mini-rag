"""US2 — answer path rejects missing skill_id for pharmacy (no live LLM)."""

from __future__ import annotations

import pytest

from services.FieldRegistry import get_field_registry
from services.rag.skills import SkillResolutionError, resolve_skill


def test_pharmacy_answer_requires_skill_binding() -> None:
    profile = get_field_registry().build_profile("pharmacy")
    with pytest.raises(SkillResolutionError) as ei:
        resolve_skill(profile, None)
    assert ei.value.code == "skill_required"
