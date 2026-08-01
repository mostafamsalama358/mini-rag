"""022 — no plan_field/plan_operation bridge on Skill runtime contract."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT

SCHEMAS = REPO_ROOT / "src" / "fields" / "schemas.py"
CONTEXT = REPO_ROOT / "src" / "services" / "rag" / "skills" / "context.py"


def test_skill_filter_profile_has_no_plan_bridge_fields() -> None:
    text = SCHEMAS.read_text(encoding="utf-8")
    assert "class SkillFilterProfile" in text
    profile_block = text.split("class SkillFilterProfile")[1].split("class SkillDefinition")[0]
    assert "plan_field" not in profile_block
    assert "plan_operation" not in profile_block


def test_skill_execution_context_has_no_plan_bridge_fields() -> None:
    text = CONTEXT.read_text(encoding="utf-8")
    ctx_block = text.split("class SkillExecutionContext")[1].split("def from_skill_and_profile")[0]
    assert "plan_field:" not in ctx_block
    assert "plan_operation:" not in ctx_block


def test_apply_bridge_module_removed_or_deprecated() -> None:
    apply_mod = REPO_ROOT / "src" / "services" / "rag" / "skills" / "apply.py"
    if apply_mod.is_file():
        text = apply_mod.read_text(encoding="utf-8")
        assert "Deprecated" in text or "deprecated" in text
