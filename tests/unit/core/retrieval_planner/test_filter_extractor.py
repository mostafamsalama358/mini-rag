"""Tests for QueryPlanFilterExtractor."""

from __future__ import annotations

import pytest

from core.query_parser.schema import ParseResult, QueryPlan
from core.retrieval_planner.filters.query_plan_extractor import QueryPlanFilterExtractor
from core.retrieval_planner.models import RetrievalPlannerConfig, compute_filter_id


@pytest.fixture
def extractor() -> QueryPlanFilterExtractor:
    return QueryPlanFilterExtractor()


def _pr(
    filters: dict | None = None,
    language: str = "en",
) -> ParseResult:
    return ParseResult(
        original_query="q",
        canonical_query="q",
        query_plan=QueryPlan(
            field="general",
            operation="lookup",
            scope="all",
            language=language,
            filters=filters or {},
            confidence=0.9,
        ),
        used_llm=False,
        latency_ms=1.0,
    )


def test_explicit_filters(extractor):
    cfg = RetrievalPlannerConfig()
    result = extractor.extract(_pr({"status": "active"}), cfg)
    explicit = [f for f in result if f.source == "explicit"]
    assert len(explicit) == 1
    assert explicit[0].field_name == "status"
    assert explicit[0].value == "active"
    assert explicit[0].operator == "eq"


def test_language_filter_implicit(extractor):
    cfg = RetrievalPlannerConfig()
    result = extractor.extract(_pr(language="en"), cfg)
    lang = [f for f in result if f.filter_type == "language"]
    assert len(lang) == 1
    assert lang[0].source == "implicit"
    assert lang[0].value == "en"
    assert lang[0].operator == "eq"


def test_filter_id_deterministic(extractor):
    cfg = RetrievalPlannerConfig()
    a = extractor.extract(_pr({"status": "active"}), cfg)
    b = extractor.extract(_pr({"status": "active"}), cfg)
    assert a[0].filter_id == b[0].filter_id
    # Language filters also match
    lang_a = [f for f in a if f.filter_type == "language"][0]
    expected = compute_filter_id("language", "language", "eq", "en")
    assert lang_a.filter_id == expected


def test_extractor_id(extractor):
    assert extractor.extractor_id == "query_plan"
