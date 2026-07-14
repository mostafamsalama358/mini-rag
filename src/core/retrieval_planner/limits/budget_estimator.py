"""Budget estimator — derives RetrievalLimits from intent + field pack defaults."""

from __future__ import annotations

from typing import Any

from core.retrieval_planner.models import QueryIntent, RetrievalLimits, RetrievalPlannerConfig

_FALLBACK = {"scope": "standard", "max_evidence_units": 5, "max_candidates": 20}


class BudgetEstimator:
    def estimate(
        self,
        intent: QueryIntent,
        config: RetrievalPlannerConfig,
    ) -> RetrievalLimits:
        defaults: dict[str, Any] = dict(
            config.budget_defaults.get(intent.category, _FALLBACK)
        )
        max_units = int(defaults.get("max_evidence_units", 5))
        max_candidates = int(defaults.get("max_candidates", max_units * 4))
        scope = str(defaults.get("scope", "standard"))

        ceiling = config.max_evidence_units_ceiling
        if ceiling is not None and max_units > ceiling:
            max_units = ceiling
            if max_candidates < max_units:
                max_candidates = max_units

        return RetrievalLimits(
            max_evidence_units=max_units,
            max_candidates=max_candidates,
            scope=scope,  # type: ignore[arg-type]
        )
