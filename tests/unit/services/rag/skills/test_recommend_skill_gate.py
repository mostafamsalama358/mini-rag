"""US6 — recommend_mode only when Skill.capabilities.recommend_mode."""

from __future__ import annotations

from fields.schemas import (
    SkillCapabilities,
    SkillDefinition,
    SkillFilterProfile,
    SkillFilterProfileFilters,
)
from services.rag.skills.context import SkillExecutionContext


def test_alternatives_enables_recommend() -> None:
    skill = SkillDefinition(
        id="alternatives",
        name="Alternatives",
        profile="indications_recommend",
        prompt="alternatives",
        capabilities=SkillCapabilities(recommend_mode=True),
    )
    profile = SkillFilterProfile(
        id="indications_recommend",
        filters=SkillFilterProfileFilters(field=["indications"]),
    )
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill,
        profile=profile,
        domain_key="pharmacy",
    )
    out = ctx.build_query_plan(language="en")
    assert out.recommend_mode is True
    assert out.operation == "recommend"
