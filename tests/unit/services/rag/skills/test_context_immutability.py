"""Unit tests for SkillExecutionContext immutability (022)."""

from __future__ import annotations

import dataclasses

import pytest

from fields.schemas import SkillDefinition, SkillFilterProfile, SkillFilterProfileFilters
from services.rag.skills.context import SkillExecutionContext


def _skill_and_profile(*, field: str = "warnings", strategy: str = "default") -> tuple:
    skill = SkillDefinition(id="warnings", name="Warnings", profile="warnings", prompt="warnings")
    profile = SkillFilterProfile(
        id="warnings",
        filters=SkillFilterProfileFilters(field=[field]),
        retrieval_strategy=strategy,  # type: ignore[arg-type]
    )
    return skill, profile


def test_context_is_frozen() -> None:
    skill, profile = _skill_and_profile()
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill, profile=profile, domain_key="pharmacy"
    )
    with pytest.raises(Exception):
        ctx.skill_id = "other"  # type: ignore[misc]


def test_with_entities_does_not_mutate_original() -> None:
    skill, profile = _skill_and_profile()
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill, profile=profile, domain_key="pharmacy"
    )
    updated = ctx.with_entities(["Panadol", "Panadol"])
    assert ctx.entities == ()
    assert updated.entities == ("Panadol",)


def test_build_query_plan_derives_field_from_profile_filters() -> None:
    skill, profile = _skill_and_profile(field="pregnancy")
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill, profile=profile, domain_key="pharmacy"
    ).with_entities(["Glucophage"])
    plan = ctx.build_query_plan(language="en")
    assert plan.field == "pregnancy"
    assert plan.entity == "Glucophage"


def test_build_query_plan_derives_operation_from_strategy() -> None:
    skill, profile = _skill_and_profile(strategy="document_lookup")
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill, profile=profile, domain_key="pharmacy"
    )
    plan = ctx.build_query_plan(language="en")
    assert plan.operation == "explain"


def test_no_plan_field_attributes_on_context() -> None:
    skill, profile = _skill_and_profile()
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill, profile=profile, domain_key="pharmacy"
    )
    assert "plan_field" not in dataclasses.fields(ctx)
    assert "plan_operation" not in [f.name for f in dataclasses.fields(ctx)]
