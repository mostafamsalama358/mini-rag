"""PlanAssembler + full pipeline integration tests."""

from __future__ import annotations

import pytest

from core.retrieval_planner.assembly import PlanAssembler
from core.retrieval_planner.clarification.confidence_based import (
    ConfidenceBasedClarificationDetector,
)
from core.retrieval_planner.entities.query_plan_resolver import QueryPlanEntityResolver
from core.retrieval_planner.filters.query_plan_extractor import QueryPlanFilterExtractor
from core.retrieval_planner.intent.rule_based import RuleBasedIntentClassifier
from core.retrieval_planner.limits.budget_estimator import BudgetEstimator
from core.retrieval_planner.models import RetrievalPlannerConfig
from core.retrieval_planner.pipeline import RetrievalPlannerPipeline
from core.retrieval_planner.strategies.config_driven import ConfigDrivenStrategySelector


def _pipeline() -> RetrievalPlannerPipeline:
    return RetrievalPlannerPipeline(
        intent_classifier=RuleBasedIntentClassifier(),
        entity_resolver=QueryPlanEntityResolver(),
        filter_extractor=QueryPlanFilterExtractor(),
        clarification_detector=ConfidenceBasedClarificationDetector(),
        strategy_selector=ConfigDrivenStrategySelector(),
        budget_estimator=BudgetEstimator(),
        assembler=PlanAssembler(),
    )


def test_factual_plan_shape(factual_parse, generic_config):
    plan = _pipeline().plan(factual_parse, generic_config)
    assert plan.clarification_required is False
    assert len(plan.retrieval_strategies) >= 1
    assert plan.retrieval_strategies[0] == "semantic"
    assert plan.intent.category == "factual"
    assert plan.intent.confidence >= 0.8
    assert plan.planner_confidence >= 0.8
    assert plan.entities[0].canonical_form == "ibuprofen"
    assert plan.retrieval_limits.scope == "narrow"
    assert plan.retrieval_limits.max_evidence_units == 5
    assert plan.retrieval_constraints.citation_required is True
    assert plan.retrieval_constraints.required_language == "en"
    assert plan.clarification_question is None
    assert plan.diagnostics is None
    assert plan.metadata.schema_version == "1.0.0"
    assert plan.metadata.plan_id.startswith("rp_")
    assert len(plan.metadata.plan_id) == 19


def test_factual_plan_id_deterministic(factual_parse, generic_config):
    pipe = _pipeline()
    a = pipe.plan(factual_parse, generic_config)
    b = pipe.plan(factual_parse, generic_config)
    assert a.metadata.plan_id == b.metadata.plan_id


def test_ambiguous_clarification(ambiguous_parse, generic_config):
    plan = _pipeline().plan(ambiguous_parse, generic_config)
    assert plan.clarification_required is True
    assert plan.retrieval_strategies == ()
    assert plan.clarification_question
    assert len(plan.clarification_question) > 0
    assert plan.planner_confidence <= 0.5


def test_domain_config_integration(factual_parse):
    generic = RetrievalPlannerConfig()
    restricted = RetrievalPlannerConfig(
        available_strategies=["keyword", "metadata", "hybrid"],
        default_strategy="keyword",
        strategy_mappings={"factual": ["semantic", "hybrid", "keyword"]},
        max_evidence_units_ceiling=3,
        budget_defaults={
            "factual": {"scope": "narrow", "max_evidence_units": 5, "max_candidates": 20},
        },
    )
    pipe = _pipeline()
    plan_g = pipe.plan(factual_parse, generic)
    plan_r = pipe.plan(factual_parse, restricted)
    assert plan_g.retrieval_strategies != plan_r.retrieval_strategies
    assert "semantic" not in plan_r.retrieval_strategies
    assert plan_r.retrieval_limits.max_evidence_units <= 3
    assert plan_g.retrieval_limits.max_evidence_units != plan_r.retrieval_limits.max_evidence_units or (
        plan_g.retrieval_strategies != plan_r.retrieval_strategies
    )
