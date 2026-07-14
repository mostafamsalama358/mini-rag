"""RetrievalPlannerPipeline — stateless orchestrator for the seven planning stages."""

from __future__ import annotations

import hashlib
import logging
import time

from core.query_parser.schema import ParseResult
from core.retrieval_planner.assembly import PlanAssembler
from core.retrieval_planner.interfaces import (
    IClarificationDetector,
    IEntityResolver,
    IFilterExtractor,
    IIntentClassifier,
    IRetrievalPlanner,
    IStrategySelector,
)
from core.retrieval_planner.limits.budget_estimator import BudgetEstimator
from core.retrieval_planner.models import (
    PlannerDiagnostics,
    RetrievalPlan,
    RetrievalPlannerConfig,
)

logger = logging.getLogger(__name__)


class RetrievalPlannerPipeline(IRetrievalPlanner):
    def __init__(
        self,
        intent_classifier: IIntentClassifier,
        entity_resolver: IEntityResolver,
        filter_extractor: IFilterExtractor,
        clarification_detector: IClarificationDetector,
        strategy_selector: IStrategySelector,
        budget_estimator: BudgetEstimator,
        assembler: PlanAssembler,
    ) -> None:
        self._intent_classifier = intent_classifier
        self._entity_resolver = entity_resolver
        self._filter_extractor = filter_extractor
        self._clarification_detector = clarification_detector
        self._strategy_selector = strategy_selector
        self._budget_estimator = budget_estimator
        self._assembler = assembler

    def plan(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> RetrievalPlan:
        t0 = time.perf_counter()

        intent = self._intent_classifier.classify(parse_result, config)
        entities = self._entity_resolver.resolve(parse_result, config)
        filters = self._filter_extractor.extract(parse_result, config)
        clarification_required, clarification_question = (
            self._clarification_detector.detect(parse_result, intent, config)
        )

        diagnostics: PlannerDiagnostics | None = None
        if config.diagnostics_enabled:
            diagnostics = PlannerDiagnostics()

        if clarification_required:
            strategies: list[str] = []
            if diagnostics is not None:
                diagnostics.clarification_trigger = "clarification_required"
        else:
            strategies = self._strategy_selector.select(
                intent, entities, filters, config
            )

        limits = self._budget_estimator.estimate(intent, config)

        upstream_conf = parse_result.query_plan.confidence
        if upstream_conf is None:
            upstream_conf = 1.0
        planner_confidence = min(intent.confidence, upstream_conf)

        if diagnostics is not None:
            diagnostics.planning_latency_ms = (time.perf_counter() - t0) * 1000.0
            diagnostics.limits_derivation = {
                "category": intent.category,
                "max_evidence_units": limits.max_evidence_units,
                "scope": limits.scope,
            }

        plan = self._assembler.assemble(
            canonical_query=parse_result.canonical_query,
            intent=intent,
            entities=entities,
            filters=filters,
            strategies=strategies,
            limits=limits,
            clarification_required=clarification_required,
            clarification_question=clarification_question,
            planner_confidence=planner_confidence,
            config=config,
            diagnostics=diagnostics,
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0
        query_id = hashlib.sha256(
            (parse_result.canonical_query or "").encode("utf-8")
        ).hexdigest()[:12]

        log_fields = {
            "query_id": query_id,
            "intent_category": intent.category,
            "strategies": list(plan.retrieval_strategies),
            "planner_confidence": plan.planner_confidence,
            "latency_ms": round(latency_ms, 3),
        }
        if clarification_required:
            logger.warning(
                "retrieval_planner clarification triggered",
                extra=log_fields,
            )
        else:
            logger.info("retrieval_planner plan complete", extra=log_fields)
        if config.diagnostics_enabled:
            logger.debug(
                "retrieval_planner diagnostics",
                extra={"query_id": query_id, "diagnostics": diagnostics},
            )

        return plan
