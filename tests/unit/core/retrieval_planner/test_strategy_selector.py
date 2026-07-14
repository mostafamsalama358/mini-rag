"""Tests for ConfigDrivenStrategySelector."""

from __future__ import annotations

import pytest

from core.retrieval_planner.models import (
    QueryIntent,
    RetrievalPlannerConfig,
)
from core.retrieval_planner.strategies.config_driven import ConfigDrivenStrategySelector

_FULL_MAPPINGS = {
    "factual": ["semantic", "hybrid"],
    "list": ["semantic", "keyword"],
    "comparative": ["semantic", "hybrid", "graph"],
    "procedural": ["semantic", "document"],
    "tabular": ["table", "semantic"],
    "navigational": ["metadata", "document"],
    "mixed": ["hybrid", "semantic", "keyword"],
}


@pytest.fixture
def selector() -> ConfigDrivenStrategySelector:
    return ConfigDrivenStrategySelector()


@pytest.fixture
def full_config() -> RetrievalPlannerConfig:
    return RetrievalPlannerConfig(strategy_mappings=dict(_FULL_MAPPINGS))


@pytest.mark.parametrize(
    "category,primary",
    [
        ("factual", "semantic"),
        ("list", "semantic"),
        ("comparative", "semantic"),
        ("procedural", "semantic"),
        ("tabular", "table"),
        ("navigational", "metadata"),
        ("mixed", "hybrid"),
    ],
)
def test_intent_primary_strategy(selector, full_config, category, primary):
    intent = QueryIntent(category=category, confidence=1.0)
    result = selector.select(intent, [], [], full_config)
    assert result[0] == primary


def test_excluded_strategy_absent(selector):
    cfg = RetrievalPlannerConfig(
        available_strategies=["semantic", "keyword"],
        strategy_mappings={"comparative": ["semantic", "hybrid", "graph"]},
    )
    intent = QueryIntent(category="comparative", confidence=1.0)
    result = selector.select(intent, [], [], cfg)
    assert "graph" not in result
    assert "hybrid" not in result
    assert "semantic" in result


def test_fallback_to_default(selector):
    cfg = RetrievalPlannerConfig(
        available_strategies=["keyword"],
        default_strategy="keyword",
        strategy_mappings={"factual": ["semantic", "hybrid"]},
    )
    intent = QueryIntent(category="factual", confidence=1.0)
    result = selector.select(intent, [], [], cfg)
    assert result == ["keyword"]


def test_mixed_multi_strategy(selector, full_config):
    intent = QueryIntent(category="mixed", confidence=0.8)
    result = selector.select(intent, [], [], full_config)
    assert len(result) > 1


def test_sc010_custom_strategy_without_code_change(selector):
    cfg = RetrievalPlannerConfig(
        available_strategies=["citations_graph", "semantic"],
        strategy_mappings={"factual": ["citations_graph", "semantic"]},
        default_strategy="semantic",
    )
    intent = QueryIntent(category="factual", confidence=1.0)
    result = selector.select(intent, [], [], cfg)
    assert "citations_graph" in result
    assert result[0] == "citations_graph"


def test_domain_pack_excludes_graph(selector):
    cfg = RetrievalPlannerConfig(
        available_strategies=["semantic", "keyword", "metadata", "hybrid"],
        strategy_mappings={"comparative": ["semantic", "hybrid", "graph"]},
    )
    intent = QueryIntent(category="comparative", confidence=1.0)
    result = selector.select(intent, [], [], cfg)
    assert "graph" not in result


def test_domain_pack_ceiling_via_budget():
    from core.retrieval_planner.limits.budget_estimator import BudgetEstimator

    est = BudgetEstimator()
    intent = QueryIntent(category="factual", confidence=1.0)
    cfg = RetrievalPlannerConfig(max_evidence_units_ceiling=3)
    limits = est.estimate(intent, cfg)
    assert limits.max_evidence_units <= 3


def test_domain_pack_different_primary(selector):
    generic = RetrievalPlannerConfig(
        strategy_mappings={"factual": ["semantic", "hybrid"]},
    )
    restricted = RetrievalPlannerConfig(
        available_strategies=["keyword", "metadata"],
        default_strategy="keyword",
        strategy_mappings={"factual": ["semantic", "keyword"]},
    )
    intent = QueryIntent(category="factual", confidence=1.0)
    a = selector.select(intent, [], [], generic)
    b = selector.select(intent, [], [], restricted)
    assert a[0] != b[0]


def test_selector_id(selector):
    assert selector.selector_id == "config_driven"


def test_tabular_first(selector, full_config):
    intent = QueryIntent(category="tabular", confidence=0.8)
    result = selector.select(intent, [], [], full_config)
    assert result[0] == "table"
