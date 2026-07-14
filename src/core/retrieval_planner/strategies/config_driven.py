"""Config-driven strategy selector — table lookup from field pack YAML."""

from __future__ import annotations

from core.retrieval_planner.interfaces import IStrategySelector
from core.retrieval_planner.models import (
    QueryFilter,
    QueryIntent,
    ResolvedEntity,
    RetrievalPlannerConfig,
    StrategyType,
)


class ConfigDrivenStrategySelector(IStrategySelector):
    @property
    def selector_id(self) -> str:
        return "config_driven"

    def select(
        self,
        intent: QueryIntent,
        entities: list[ResolvedEntity],
        filters: list[QueryFilter],
        config: RetrievalPlannerConfig,
    ) -> list[StrategyType]:
        del entities, filters
        mapped = list(config.strategy_mappings.get(intent.category, []))
        available = set(config.available_strategies)
        selected = [s for s in mapped if s in available]

        if not selected:
            fallback = config.default_strategy
            if fallback not in available and available:
                fallback = next(iter(sorted(available)))
            selected = [fallback]

        return selected
