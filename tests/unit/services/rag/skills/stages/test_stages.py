"""Unit tests for Skill pipeline stages (022)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from fields.schemas import SkillDefinition, SkillFilterProfile, SkillValidationRules
from services.rag.skills.context import SkillExecutionContext
from services.rag.skills.entity_parse import EntityParseResult
from services.rag.skills.stages.entity_parse_stage import EntityParseStage
from services.rag.skills.stages.formatting import FormattingStage
from services.rag.skills.stages.validation import SkillValidationStage


def _skill_ctx(**overrides) -> SkillExecutionContext:
    skill = SkillDefinition(
        id="interactions",
        name="Interactions",
        profile="pair",
        prompt="interactions",
        validation=SkillValidationRules(require_medicine_pair=True),
    )
    profile = SkillFilterProfile(id="pair", retrieval_strategy="pair_lookup")
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill,
        profile=profile,
        domain_key="pharmacy",
    )
    if overrides:
        return ctx.with_entities(overrides.get("entities", []))
    return ctx


@pytest.mark.asyncio
async def test_entity_parse_stage_returns_updated_skill_ctx(monkeypatch) -> None:
    stage = EntityParseStage()
    skill_ctx = _skill_ctx()
    parse_service = MagicMock()
    parse_service._load_catalog_for_parser = AsyncMock(return_value=([], {}))

    entity_result = EntityParseResult(
        entities=["Aspirin", "Warfarin"],
        primary_entity="Aspirin",
        canonical_query="Aspirin Warfarin interaction",
    )

    monkeypatch.setattr(
        "services.rag.skills.stages.entity_parse_stage.entity_parse_async",
        AsyncMock(return_value=entity_result),
    )
    result = await stage.execute(
        SimpleNamespace(),
        skill_ctx=skill_ctx,
        query="Aspirin with Warfarin",
        project=SimpleNamespace(project_id=1),
        profile=SimpleNamespace(domain_key="pharmacy", parser_profile=SimpleNamespace()),
        generation_client=None,
        parse_service=parse_service,
    )

    assert result.status == "completed"
    updated = result.payload["skill_ctx"]
    assert updated.entities == ("Aspirin", "Warfarin")
    assert updated is not skill_ctx


@pytest.mark.asyncio
async def test_validation_stage_clarifies_on_missing_pair() -> None:
    stage = SkillValidationStage()
    skill_ctx = _skill_ctx()
    result = await stage.execute(
        SimpleNamespace(),
        skill_ctx=skill_ctx,
        query="hello",
    )
    assert result.status == "clarification"
    assert "two medicines" in (result.payload.get("clarification") or "").lower()


@pytest.mark.asyncio
async def test_validation_stage_passes_with_pair() -> None:
    stage = SkillValidationStage()
    skill_ctx = _skill_ctx().with_entities(["Aspirin", "Warfarin"])
    result = await stage.execute(
        SimpleNamespace(),
        skill_ctx=skill_ctx,
        query="Aspirin with Warfarin",
    )
    assert result.status == "completed"
    assert result.payload.get("validated") is True


@pytest.mark.asyncio
async def test_formatting_stage_builds_pipeline_answer_response() -> None:
    stage = FormattingStage()
    result = await stage.execute(
        SimpleNamespace(),
        answer="Safe combination.",
        full_prompt="prompt",
        chat_history=[],
        needs_clarification=False,
    )
    response = result.payload["response"]
    assert response.answer == "Safe combination."
    assert response.needs_clarification is False


def test_formatting_clarification_response() -> None:
    response = FormattingStage.clarification_response("Pick a skill.")
    assert response.needs_clarification is True
    assert response.answer == "Pick a skill."
