"""Unit tests for SkillDefinition / SkillFilterProfile schemas (021)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fields.schemas import SkillDefinition, SkillFilterProfile, SkillFilterProfileFilters


def test_skill_rejects_embedded_filters() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(
            {
                "id": "interactions",
                "name": "Interactions",
                "profile": "drug_interactions",
                "prompt": "x",
                "filters": {"field": ["interactions"]},
            }
        )


def test_skill_rejects_field_and_operation() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(
            {
                "id": "interactions",
                "name": "Interactions",
                "profile": "drug_interactions",
                "prompt": "interactions",
                "field": "interactions",
                "operation": "list",
            }
        )


def test_skill_filter_profile_ok() -> None:
    p = SkillFilterProfile(
        id="drug_interactions",
        filters=SkillFilterProfileFilters(field=["interactions"], source=["leaflet"]),
        retrieval_strategy="pair_lookup",
    )
    assert p.filters.field == ["interactions"]
    assert p.retrieval_strategy == "pair_lookup"


def test_skill_definition_profile_only() -> None:
    s = SkillDefinition(
        id="interactions",
        name="Interactions",
        profile="drug_interactions",
        prompt="interactions",
        citation_policy="strict",
        response_schema={"type": "object"},
    )
    assert s.profile == "drug_interactions"
    assert s.citation_policy == "strict"
    assert s.response_schema == {"type": "object"}
    dumped = s.model_dump()
    assert "field" not in dumped or dumped.get("field") is None
    assert "operation" not in dumped or dumped.get("operation") is None
