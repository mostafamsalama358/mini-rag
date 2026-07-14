"""Registry mapping strategy ids to Retrieval Planner implementations."""

from __future__ import annotations

from core.retrieval_planner.errors import StrategyNotFoundError
from core.retrieval_planner.interfaces import (
    IClarificationDetector,
    IEntityResolver,
    IFilterExtractor,
    IIntentClassifier,
    IStrategySelector,
)
from core.retrieval_planner.models import RetrievalPlannerConfig


class RetrievalPlannerRegistry:
    def __init__(self) -> None:
        self._intent_classifiers: dict[str, IIntentClassifier] = {}
        self._entity_resolvers: dict[str, IEntityResolver] = {}
        self._filter_extractors: dict[str, IFilterExtractor] = {}
        self._strategy_selectors: dict[str, IStrategySelector] = {}
        self._clarification_detectors: dict[str, IClarificationDetector] = {}

    def register_intent_classifier(self, impl: IIntentClassifier) -> None:
        self._intent_classifiers[impl.classifier_id] = impl

    def register_entity_resolver(self, impl: IEntityResolver) -> None:
        self._entity_resolvers[impl.resolver_id] = impl

    def register_filter_extractor(self, impl: IFilterExtractor) -> None:
        self._filter_extractors[impl.extractor_id] = impl

    def register_strategy_selector(self, impl: IStrategySelector) -> None:
        self._strategy_selectors[impl.selector_id] = impl

    def register_clarification_detector(self, impl: IClarificationDetector) -> None:
        self._clarification_detectors[impl.detector_id] = impl

    def register_defaults(self) -> None:
        """Register built-in default implementations."""
        from core.retrieval_planner.clarification.confidence_based import (
            ConfidenceBasedClarificationDetector,
        )
        from core.retrieval_planner.entities.query_plan_resolver import (
            QueryPlanEntityResolver,
        )
        from core.retrieval_planner.filters.query_plan_extractor import (
            QueryPlanFilterExtractor,
        )
        from core.retrieval_planner.intent.rule_based import RuleBasedIntentClassifier
        from core.retrieval_planner.strategies.config_driven import (
            ConfigDrivenStrategySelector,
        )

        self.register_intent_classifier(RuleBasedIntentClassifier())
        self.register_entity_resolver(QueryPlanEntityResolver())
        self.register_filter_extractor(QueryPlanFilterExtractor())
        self.register_strategy_selector(ConfigDrivenStrategySelector())
        self.register_clarification_detector(ConfidenceBasedClarificationDetector())

    def build_pipeline(self, config: RetrievalPlannerConfig):
        from core.retrieval_planner.assembly import PlanAssembler
        from core.retrieval_planner.limits.budget_estimator import BudgetEstimator
        from core.retrieval_planner.pipeline import RetrievalPlannerPipeline

        return RetrievalPlannerPipeline(
            intent_classifier=self._get(self._intent_classifiers, config.intent_classifier, "intent_classifier"),
            entity_resolver=self._get(self._entity_resolvers, config.entity_resolver, "entity_resolver"),
            filter_extractor=self._get(self._filter_extractors, config.filter_extractor, "filter_extractor"),
            clarification_detector=self._get(
                self._clarification_detectors,
                config.clarification_detector,
                "clarification_detector",
            ),
            strategy_selector=self._get(
                self._strategy_selectors, config.strategy_selector, "strategy_selector"
            ),
            budget_estimator=BudgetEstimator(),
            assembler=PlanAssembler(),
        )

    @staticmethod
    def _get(store: dict, strategy_id: str, kind: str):
        if strategy_id not in store:
            raise StrategyNotFoundError(f"unknown {kind} strategy: {strategy_id!r}")
        return store[strategy_id]


# Module-level singleton for convenience.
default_registry = RetrievalPlannerRegistry()
