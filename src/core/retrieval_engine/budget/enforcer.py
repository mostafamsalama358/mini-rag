"""Budget enforcement for candidate and evidence caps."""

from __future__ import annotations

from core.retrieval_engine.models import RawCandidate, RetrievedCandidate
from core.retrieval_planner.models import RetrievalLimits


class BudgetEnforcer:
    def apply_candidate_cap(
        self,
        candidates: list[RawCandidate],
        limits: RetrievalLimits,
    ) -> list[RawCandidate]:
        if limits.max_candidates <= 0:
            return []
        return list(candidates[: limits.max_candidates])

    def apply_evidence_cap(
        self,
        candidates: list[RetrievedCandidate],
        limits: RetrievalLimits,
    ) -> list[RetrievedCandidate]:
        if limits.max_evidence_units <= 0:
            return []
        return list(candidates[: limits.max_evidence_units])

    def check_latency_budget(self, elapsed_ms: float, budget_ms: int | None) -> bool:
        """Return True when the latency budget has been exceeded."""
        if budget_ms is None:
            return False
        return elapsed_ms > budget_ms
