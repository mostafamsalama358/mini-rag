"""021 — Skill-enabled path must not classify skills from text."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT

REGISTRY = REPO_ROOT / "src" / "services" / "rag" / "skills" / "registry.py"


def test_resolve_skill_uses_client_id_only() -> None:
    text = REGISTRY.read_text(encoding="utf-8")
    assert "resolve_skill" in text
    assert "difflib" not in text
    assert "SequenceMatcher" not in text
    assert "classify_skill" not in text
