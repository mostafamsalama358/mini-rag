"""Budget enforcement for candidate and evidence caps."""

from __future__ import annotations

from core.retrieval_engine.models import RawCandidate, RetrievedCandidate
from core.retrieval_planner.models import RetrievalLimits

# Drop fused candidates that are far weaker than the top hit — reduces
# distractor pollution in top-k without requiring a live reranker.
_DEFAULT_RELATIVE_SCORE_FLOOR = 0.15


class BudgetEnforcer:
    def apply_candidate_cap(
        self,
        candidates: list[RawCandidate],
        limits: RetrievalLimits,
        *,
        relative_score_floor: float = _DEFAULT_RELATIVE_SCORE_FLOOR,
    ) -> list[RawCandidate]:
        if limits.max_candidates <= 0:
            return []
        filtered = self.apply_relative_score_floor(
            candidates, relative_score_floor=relative_score_floor
        )
        return list(filtered[: limits.max_candidates])

    def apply_relative_score_floor(
        self,
        candidates: list[RawCandidate],
        *,
        relative_score_floor: float = _DEFAULT_RELATIVE_SCORE_FLOOR,
    ) -> list[RawCandidate]:
        if not candidates or relative_score_floor <= 0:
            return list(candidates)
        top = max(float(c.raw_score or 0.0) for c in candidates)
        if top <= 0:
            return list(candidates)
        floor = top * relative_score_floor
        kept = [c for c in candidates if float(c.raw_score or 0.0) >= floor]
        return kept or list(candidates[:1])

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
