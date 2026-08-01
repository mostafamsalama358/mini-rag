"""021 — recommend_mode gated by Skill capability, not free-text intent alone."""

from __future__ import annotations

from fields.schemas import (
    SkillCapabilities,
    SkillDefinition,
    SkillFilterProfile,
    SkillFilterProfileFilters,
)
from services.rag.skills.context import SkillExecutionContext


def test_leaflet_skill_clears_recommend_mode() -> None:
    skill = SkillDefinition(
        id="leaflet",
        name="Leaflet",
        profile="leaflet_general",
        prompt="leaflet",
        capabilities=SkillCapabilities(recommend_mode=False),
    )
    profile = SkillFilterProfile(
        id="leaflet_general",
        filters=SkillFilterProfileFilters(field=["indications"]),
        retrieval_strategy="document_lookup",
    )
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill,
        profile=profile,
        domain_key="pharmacy",
    )
    out = ctx.build_query_plan(language="en")
    assert out.recommend_mode is False
    assert out.operation == "explain"
