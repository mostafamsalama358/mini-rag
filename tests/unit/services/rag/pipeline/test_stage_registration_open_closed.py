"""US4 — PipelineBuilder open/closed: extra stage without orchestrator edits."""

from __future__ import annotations

from pathlib import Path

from services.rag.pipeline.builder import PipelineBuilder
from services.rag.skills.stages.contracts import StageResult


class _NoOp:
    name = "noop_extension"

    async def execute(self, ctx, **kwargs):
        return StageResult(stage=self.name, status="ok", payload={"noop": True})


def test_register_noop_without_editing_orchestrator() -> None:
    chain = PipelineBuilder().register(_NoOp()).build()
    assert len(chain) == 1
    assert chain[0].name == "noop_extension"

    repo = Path(__file__).resolve().parents[5]
    orch = repo / "src" / "services" / "rag" / "pipeline" / "skill_orchestrator.py"
    text = orch.read_text(encoding="utf-8")
    assert "noop_extension" not in text
