"""Tests for QueryPlanEntityResolver."""

from __future__ import annotations

import pytest

from core.query_parser.schema import ParseResult, QueryPlan
from core.retrieval_planner.entities.query_plan_resolver import QueryPlanEntityResolver
from core.retrieval_planner.models import RetrievalPlannerConfig, compute_entity_id


@pytest.fixture
def resolver() -> QueryPlanEntityResolver:
    return QueryPlanEntityResolver()


def _pr(entities: list[str], query: str = "q") -> ParseResult:
    return ParseResult(
        original_query=query,
        canonical_query=query,
        query_plan=QueryPlan(
            field="general",
            operation="lookup",
            scope="all",
            language="en",
            entities=entities,
            confidence=0.9,
        ),
        used_llm=False,
        latency_ms=1.0,
    )


def test_wraps_entities(resolver):
    cfg = RetrievalPlannerConfig()
    result = resolver.resolve(_pr(["ibuprofen"]), cfg)
    assert len(result) == 1
    assert result[0].raw_text == "ibuprofen"
    assert result[0].canonical_form == "ibuprofen"
    assert result[0].entity_id == compute_entity_id("ibuprofen", result[0].entity_type)


def test_alias_resolution(resolver):
    cfg = RetrievalPlannerConfig(entity_aliases={"ASA": "aspirin"})
    result = resolver.resolve(_pr(["ASA"]), cfg)
    assert result[0].canonical_form == "aspirin"
    assert result[0].raw_text == "ASA"


def test_entity_id_deterministic(resolver):
    cfg = RetrievalPlannerConfig()
    a = resolver.resolve(_pr(["ibuprofen"]), cfg)
    b = resolver.resolve(_pr(["ibuprofen"]), cfg)
    assert a[0].entity_id == b[0].entity_id


def test_empty_entities(resolver):
    cfg = RetrievalPlannerConfig()
    assert resolver.resolve(_pr([]), cfg) == []


def test_entity_type_patterns(resolver):
    cfg = RetrievalPlannerConfig(
        entity_type_patterns=[{"pattern": "ibuprofen|aspirin", "entity_type": "drug"}]
    )
    result = resolver.resolve(_pr(["ibuprofen"]), cfg)
    assert result[0].entity_type == "drug"


def test_canonical_defaults_to_raw(resolver):
    cfg = RetrievalPlannerConfig()
    result = resolver.resolve(_pr(["unknown_thing"]), cfg)
    assert result[0].canonical_form == "unknown_thing"


def test_resolver_id(resolver):
    assert resolver.resolver_id == "query_plan"
