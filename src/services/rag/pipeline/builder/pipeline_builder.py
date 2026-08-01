"""Declarative stage registration — no orchestrator edits per Skill (022)."""

from __future__ import annotations

from typing import Any


class PipelineBuilder:
    """Register stage executors in order; ``build()`` returns the frozen sequence."""

    def __init__(self) -> None:
        self._stages: list[Any] = []

    def register(self, stage: Any) -> "PipelineBuilder":
        """Append a stage executor (must expose ``name`` and ``execute``)."""
        self._stages.append(stage)
        return self

    def build(self) -> tuple[Any, ...]:
        """Return an immutable tuple of registered stages."""
        return tuple(self._stages)
