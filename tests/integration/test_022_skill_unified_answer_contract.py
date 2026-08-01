"""022 — Skill traffic uses SkillRuntimeOrchestrator; router avoids legacy force."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT


def test_skill_runtime_orchestrator_exists() -> None:
    from services.rag.pipeline.skill_orchestrator import SkillRuntimeOrchestrator

    assert SkillRuntimeOrchestrator is not None


def test_router_uses_profile_has_skills_without_legacy_force() -> None:
    router_path = REPO_ROOT / "src" / "services" / "rag" / "pipeline" / "router.py"
    text = router_path.read_text(encoding="utf-8")
    assert "profile_has_skills" in text
    assert 'if getattr(profile, "skills", None):' not in text
    assert "_skill_runtime.execute" in text
