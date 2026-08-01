"""US3 — two Skills sharing one profile observe the same filters."""

from __future__ import annotations

from fields.schemas import SkillDefinition, SkillFilterProfile, SkillFilterProfileFilters
from services.rag.skills.context import SkillExecutionContext
from services.rag.skills.filters import effective_filters


def test_shared_profile_filters() -> None:
    shared = SkillFilterProfile(
        id="warnings",
        filters=SkillFilterProfileFilters(field=["warnings", "precautions"]),
    )
    assert effective_filters(shared)["field"] == ["warnings", "precautions"]
    for skill_id in ("warnings", "consultations"):
        skill = SkillDefinition(
            id=skill_id,
            name=skill_id,
            profile="warnings",
            prompt=skill_id,
        )
        ctx = SkillExecutionContext.from_skill_and_profile(
            skill=skill,
            profile=shared,
            domain_key="pharmacy",
        )
        assert ctx.metadata_filters["field"] == ["warnings", "precautions"]
