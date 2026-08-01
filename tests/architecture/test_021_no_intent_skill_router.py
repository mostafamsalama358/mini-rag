"""021 — no intent→skill_id router for Skill-enabled pharmacy."""

from __future__ import annotations

from pathlib import Path

from tests.architecture._repo import REPO_ROOT

RAG = REPO_ROOT / "src" / "services" / "rag"


def test_no_function_maps_intent_to_skill_id() -> None:
    banned = ("intent_to_skill", "classify_skill", "detect_skill", "alias_to_skill")
    hits: list[str] = []
    for path in RAG.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in banned:
            if token in text:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{token}")
    assert not hits, hits
