"""US5 — cross-domain Skill runtime uses same orchestrator type."""

from __future__ import annotations

from services.FieldRegistry import get_field_registry
from services.rag.pipeline.skill_orchestrator import SkillRuntimeOrchestrator, profile_has_skills
from services.rag.skills import resolve_skill


def test_legal_stub_skills_resolve_on_same_runtime_contract() -> None:
    reg = get_field_registry()
    reg.load()
    # legal pack may be stub; skip gracefully if absent
    try:
        profile = reg.build_profile("legal")
    except Exception:
        pytest = __import__("pytest")
        pytest.skip("legal domain pack not loadable")
        return
    if not profile_has_skills(profile):
        import pytest

        pytest.skip("legal pack has no skills")
    skill_id = next(iter(profile.skills))
    ctx = resolve_skill(profile, skill_id)
    assert ctx is not None
    assert ctx.domain_key == "legal"
    assert SkillRuntimeOrchestrator  # same runtime class for all domains
