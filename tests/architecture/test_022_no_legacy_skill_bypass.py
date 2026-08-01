"""022 — Skill-bound traffic must not force legacy executor."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT

ROUTER = REPO_ROOT / "src" / "services" / "rag" / "pipeline" / "router.py"


def test_no_skill_legacy_force_in_router() -> None:
    text = ROUTER.read_text(encoding="utf-8")
    assert 'if getattr(profile, "skills", None):' not in text, (
        "PipelineRouter still forces LegacyPipelineExecutor for Skill-enabled profiles"
    )
