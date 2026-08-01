"""Unit tests for declarative PipelineBuilder (022)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.rag.pipeline.builder import PipelineBuilder
from services.rag.skills.stages.contracts import StageResult


@dataclass(frozen=True)
class _StubStage:
    _name: str

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, ctx, **kwargs) -> StageResult:
        return StageResult(stage=self._name, status="completed", payload={"ctx": ctx})


def test_register_and_build_returns_tuple_in_order() -> None:
    builder = PipelineBuilder()
    s1 = _StubStage("parse")
    s2 = _StubStage("retrieve")
    builder.register(s1).register(s2)
    stages = builder.build()
    assert stages == (s1, s2)
    assert isinstance(stages, tuple)


@pytest.mark.asyncio
async def test_built_stages_are_executable() -> None:
    stage = _StubStage("parse")
    pipeline = PipelineBuilder().register(stage).build()
    result = await pipeline[0].execute({"q": "test"})
    assert result.stage == "parse"
    assert result.status == "completed"
