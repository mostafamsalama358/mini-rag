"""022 — Skill orchestration must not live in answer_service."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT

ANSWER = REPO_ROOT / "src" / "services" / "rag" / "answer_service.py"


def test_answer_service_no_skill_orchestration() -> None:
    text = ANSWER.read_text(encoding="utf-8")
    banned = (
        "entity_parse_async",
        "rag_skill_bound",
        "resolve_skill(",
        "load_skill_prompt",
        "evaluate_skill_validation",
    )
    hits = [token for token in banned if token in text]
    assert not hits, f"Skill orchestration tokens in answer_service: {hits}"


def test_answer_service_delegates_skill_profiles() -> None:
    text = ANSWER.read_text(encoding="utf-8")
    assert "profile_has_skills(profile)" in text
    assert "execute_as_legacy_tuple" in text
    assert 'raise RuntimeError("Skill runtime not configured")' in text
