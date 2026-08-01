"""US4 — Skill injects field via Profile (build_query_plan), not Skill.field."""

from __future__ import annotations

from fields.schemas import (
    SkillDefinition,
    SkillFilterProfile,
    SkillFilterProfileFilters,
)
from services.rag.skills.context import SkillExecutionContext


def _ctx(skill_id: str, field: str) -> SkillExecutionContext:
    skill = SkillDefinition(
        id=skill_id,
        name=skill_id,
        profile=field,
        prompt=skill_id,
    )
    profile = SkillFilterProfile(
        id=field,
        filters=SkillFilterProfileFilters(field=[field]),
    )
    return SkillExecutionContext.from_skill_and_profile(
        skill=skill,
        profile=profile,
        domain_key="pharmacy",
    ).with_entities(["Glucophage"])


def test_same_text_different_skill_fields() -> None:
    preg = _ctx("pregnancy", "pregnancy").build_query_plan(language="en")
    side = _ctx("side_effects", "side_effects").build_query_plan(language="en")
    assert preg.field == "pregnancy"
    assert side.field == "side_effects"
    assert preg.entity == side.entity == "Glucophage"
