"""Polish — default profile has no silent broaden."""

from __future__ import annotations

from fields.schemas import SkillFilterProfile, SkillFilterProfileFilters
from services.rag.skills.filters import effective_filters


def test_default_fallback_absent() -> None:
    profile = SkillFilterProfile(
        id="dosage",
        filters=SkillFilterProfileFilters(field=["dosage"]),
    )
    assert profile.fallback is None
    assert effective_filters(profile)["field"] == ["dosage"]
