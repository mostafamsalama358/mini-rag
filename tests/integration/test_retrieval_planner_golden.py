"""Golden plan suite for Retrieval Planner (SC-004, SC-005, SC-002)."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

import pytest

from core.query_parser.schema import ParseResult, QueryPlan
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


@dataclass(frozen=True)
class GoldenCase:
    label: str
    query: str
    operation: str
    entities: list[str]
    confidence: float
    expected_category: str
    expected_primary_strategy: str | None  # None when clarification expected
    ambiguous: bool
    needs_clarification: bool = False
    clarification_prompt: str | None = None


GOLDEN_CASES: list[GoldenCase] = [
    GoldenCase(
        "factual_ibuprofen",
        "What are the contraindications for ibuprofen?",
        "lookup",
        ["ibuprofen"],
        0.95,
        "factual",
        "semantic",
        False,
    ),
    GoldenCase(
        "factual_aspirin",
        "What is the half-life of aspirin?",
        "lookup",
        ["aspirin"],
        0.9,
        "factual",
        "semantic",
        False,
    ),
    GoldenCase(
        "list_interactions",
        "list all drug interactions for warfarin",
        "list",
        ["warfarin"],
        0.9,
        "list",
        "semantic",
        False,
    ),
    GoldenCase(
        "list_side_effects",
        "list the side effects of metformin",
        "list",
        ["metformin"],
        0.88,
        "list",
        "semantic",
        False,
    ),
    GoldenCase(
        "comparative_vs",
        "compare aspirin versus ibuprofen for pain",
        "compare",
        ["aspirin", "ibuprofen"],
        0.92,
        "comparative",
        "semantic",
        False,
    ),
    GoldenCase(
        "procedural_how_to",
        "how to administer insulin subcutaneous injection",
        "explain",
        ["insulin"],
        0.9,
        "procedural",
        "semantic",
        False,
    ),
    GoldenCase(
        "tabular_dosage",
        "Show me the dosage table for aspirin",
        "lookup",
        ["aspirin"],
        0.9,
        "tabular",
        "table",
        False,
    ),
    GoldenCase(
        "tabular_schedule",
        "What is the dosing schedule table for antibiotics",
        "lookup",
        ["antibiotics"],
        0.85,
        "tabular",
        "table",
        False,
    ),
    GoldenCase(
        "navigational_where",
        "where is the contraindications section",
        "lookup",
        [],
        0.85,
        "navigational",
        "metadata",
        False,
    ),
    GoldenCase(
        "count_factual",
        "how many interactions does warfarin have",
        "count",
        ["warfarin"],
        0.9,
        "factual",
        "semantic",
        False,
    ),
    GoldenCase(
        "mixed_compare_list",
        "compare and list the side effects of aspirin versus ibuprofen",
        "compare",
        ["aspirin", "ibuprofen"],
        0.85,
        "mixed",
        "hybrid",
        False,
    ),
    GoldenCase(
        "ambiguous_vague",
        "Tell me about it",
        "unsupported",
        [],
        0.2,
        "factual",
        None,
        True,
    ),
    GoldenCase(
        "ambiguous_upstream",
        "show me that one",
        "lookup",
        [],
        0.5,
        "factual",
        None,
        True,
        needs_clarification=True,
        clarification_prompt="Which document are you referring to?",
    ),
    GoldenCase(
        "empty_query",
        "   ",
        "unsupported",
        [],
        0.0,
        "factual",
        None,
        True,
    ),
    GoldenCase(
        "keyword_list_all",
        "list all approved dosages",
        "list",
        ["dosages"],
        0.9,
        "list",
        "semantic",
        False,
    ),
    GoldenCase(
        "procedural_steps",
        "steps to prepare a sterile solution",
        "explain",
        [],
        0.88,
        "procedural",
        "semantic",
        False,
    ),
]


def _parse(case: GoldenCase) -> ParseResult:
    return ParseResult(
        original_query=case.query,
        canonical_query=case.query,
        query_plan=QueryPlan(
            field="general",
            operation=case.operation,  # type: ignore[arg-type]
            scope="all",
            language="en",
            entities=case.entities,
            confidence=case.confidence,
            needs_clarification=case.needs_clarification,
            clarification_prompt=case.clarification_prompt,
        ),
        used_llm=False,
        latency_ms=1.0,
    )


@pytest.fixture(scope="module")
def pipeline() -> RetrievalPlannerPipeline:
    return RetrievalPlannerPipeline(
        intent_classifier=RuleBasedIntentClassifier(),
        entity_resolver=QueryPlanEntityResolver(),
        filter_extractor=QueryPlanFilterExtractor(),
        clarification_detector=ConfidenceBasedClarificationDetector(),
        strategy_selector=ConfigDrivenStrategySelector(),
        budget_estimator=BudgetEstimator(),
        assembler=PlanAssembler(),
    )


@pytest.fixture(scope="module")
def config() -> RetrievalPlannerConfig:
    return RetrievalPlannerConfig()


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda c: c.label)
def test_golden_plan(pipeline, config, case: GoldenCase):
    plan = pipeline.plan(_parse(case), config)

    # Determinism
    plan_b = pipeline.plan(_parse(case), config)
    assert plan.metadata.plan_id == plan_b.metadata.plan_id
    assert plan.metadata.schema_version == "1.0.0"

    if case.ambiguous:
        assert plan.clarification_required is True
        assert plan.retrieval_strategies == ()
        assert plan.clarification_question
    else:
        assert plan.clarification_required is False
        assert plan.intent.category == case.expected_category
        assert plan.retrieval_strategies
        assert plan.retrieval_strategies[0] == case.expected_primary_strategy


def test_golden_strategy_accuracy(pipeline, config):
    """SC-004: ≥ 90% of non-ambiguous golden queries get expected primary strategy."""
    clear = [c for c in GOLDEN_CASES if not c.ambiguous]
    hits = 0
    for case in clear:
        plan = pipeline.plan(_parse(case), config)
        if (
            not plan.clarification_required
            and plan.retrieval_strategies
            and plan.retrieval_strategies[0] == case.expected_primary_strategy
            and plan.intent.category == case.expected_category
        ):
            hits += 1
    accuracy = hits / len(clear)
    assert accuracy >= 0.90, f"strategy accuracy {accuracy:.2%} < 90% ({hits}/{len(clear)})"


def test_clarification_precision(pipeline, config):
    """SC-005: ≥ 85% precision — clear queries must not trigger clarification."""
    clear = [c for c in GOLDEN_CASES if not c.ambiguous]
    false_positives = 0
    for case in clear:
        plan = pipeline.plan(_parse(case), config)
        if plan.clarification_required:
            false_positives += 1
    precision = 1.0 - (false_positives / len(clear))
    assert precision >= 0.85, (
        f"clarification precision {precision:.2%} < 85% "
        f"({false_positives} false positives / {len(clear)})"
    )


def test_benchmark_p95(pipeline, config, request):
    """SC-002: p95 planning latency ≤ 50 ms (opt-in via --benchmark)."""
    if not request.config.getoption("--benchmark", default=False):
        pytest.skip("pass --benchmark to run latency validation")

    latencies: list[float] = []
    for case in GOLDEN_CASES:
        pr = _parse(case)
        for _ in range(100):
            t0 = time.perf_counter()
            pipeline.plan(pr, config)
            latencies.append((time.perf_counter() - t0) * 1000.0)

    p95 = statistics.quantiles(latencies, n=20)[18]  # ~95th percentile
    assert p95 <= 50.0, f"p95 latency {p95:.2f} ms exceeds 50 ms"
