"""US3 — profile filter expansion without Skill mutation."""

from __future__ import annotations

from fields.schemas import SkillDefinition, SkillFilterProfile, SkillFilterProfileFilters
from services.rag.skills.filters import effective_filters


def test_profile_filters_independent_of_skill() -> None:
    skill = SkillDefinition(
        id="interactions",
        name="Interactions",
        profile="drug_interactions",
        prompt="interactions",
    )
    narrow = SkillFilterProfile(
        id="drug_interactions",
        filters=SkillFilterProfileFilters(field=["interactions"]),
    )
    wide = SkillFilterProfile(
        id="drug_interactions",
        filters=SkillFilterProfileFilters(
            field=["interactions", "warnings", "precautions"]
        ),
    )
    assert skill.profile == "drug_interactions"
    assert effective_filters(narrow)["field"] == ["interactions"]
    assert "warnings" in effective_filters(wide)["field"]
    assert skill.model_dump()["profile"] == "drug_interactions"
