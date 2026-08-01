"""Immutable stage contracts — input/output/failure/side-effects (022)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class StageContract:
    """Declarative I/O and failure semantics for a pipeline stage."""

    name: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class StageResult:
    """Immutable output of a single pipeline stage execution."""

    stage: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class StageExecutor(Protocol):
    """Plugin contract for a declarative pipeline stage."""

    @property
    def name(self) -> str:
        """Stable stage identifier used in traces and registration."""

    async def execute(self, ctx: Any, **kwargs: Any) -> StageResult:
        """Run the stage against ``ctx`` and optional injected ports.

        Inputs (via ``ctx`` / ``kwargs``): domain-specific execution context
        and stage ports (search, parse, generate, …).

        Outputs: ``StageResult`` with ``payload`` holding stage artifacts.

        Failures: return ``status="failed"`` with ``error`` set; do not mutate
        ``ctx``.

        Side effects: logging/metrics only unless a port explicitly performs
        external I/O (retrieval, generation).
        """
