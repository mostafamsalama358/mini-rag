"""Incremental retrieval trace builder."""

from __future__ import annotations

from core.retrieval_engine.models import RetrievalStepTrace, RetrievalTrace


class RetrievalTracer:
    """Mutable accumulator used during a single pipeline execution."""

    def __init__(self) -> None:
        self._steps: list[RetrievalStepTrace] = []
        self._violations: list[str] = []

    def append_step(self, step: RetrievalStepTrace) -> None:
        self._steps.append(step)

    def record_violation(self, message: str) -> None:
        self._violations.append(message)

    def build_trace(self, plan_id: str, total_latency_ms: float) -> RetrievalTrace:
        return RetrievalTrace(
            plan_id=plan_id,
            steps=tuple(self._steps),
            total_latency_ms=total_latency_ms,
            constraint_violations=tuple(self._violations),
        )
