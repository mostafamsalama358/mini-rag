"""022 — SkillExecutionContext and stage results must be immutable."""

from __future__ import annotations

import dataclasses

from tests.architecture._repo import REPO_ROOT

CONTEXT = REPO_ROOT / "src" / "services" / "rag" / "skills" / "context.py"
STAGES = REPO_ROOT / "src" / "services" / "rag" / "skills" / "stages" / "contracts.py"


def test_skill_execution_context_is_frozen_dataclass() -> None:
    text = CONTEXT.read_text(encoding="utf-8")
    assert "@dataclass(frozen=True)" in text
    assert "class SkillExecutionContext" in text


def test_stage_result_is_frozen_dataclass() -> None:
    text = STAGES.read_text(encoding="utf-8")
    assert "@dataclass(frozen=True)" in text
    assert "class StageResult" in text


def test_context_with_entities_returns_new_instance() -> None:
    """Runtime check: frozen + replace pattern."""
    from fields.schemas import SkillDefinition, SkillFilterProfile
    from services.rag.skills.context import SkillExecutionContext

    skill = SkillDefinition(id="s", name="S", profile="p", prompt="s")
    profile = SkillFilterProfile(id="p")
    ctx = SkillExecutionContext.from_skill_and_profile(
        skill=skill, profile=profile, domain_key="generic"
    )
    assert dataclasses.is_dataclass(ctx) and ctx.__dataclass_fields__
    updated = ctx.with_entities(["Aspirin"])
    assert updated is not ctx
    assert ctx.entities == ()
