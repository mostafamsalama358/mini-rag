"""Shared ParseResult fixtures for Retrieval Planner unit tests."""

from __future__ import annotations

import pytest

from core.query_parser.schema import ParseResult, QueryPlan
from core.retrieval_planner.models import RetrievalPlannerConfig


def pytest_addoption(parser):
    parser.addoption(
        "--benchmark",
        action="store_true",
        default=False,
        help="Run latency benchmark assertions for retrieval planner",
    )


def _parse(
    *,
    query: str,
    operation: str,
    entities: list[str] | None = None,
    language: str = "en",
    confidence: float | None = 0.95,
    needs_clarification: bool = False,
    clarification_prompt: str | None = None,
    filters: dict | None = None,
    field: str = "general",
    scope: str = "all",
) -> ParseResult:
    plan = QueryPlan(
        field=field,
        operation=operation,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        language=language,
        entities=entities or [],
        filters=filters or {},
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_prompt=clarification_prompt,
    )
    return ParseResult(
        original_query=query,
        canonical_query=query,
        query_plan=plan,
        used_llm=False,
        latency_ms=1.0,
    )


@pytest.fixture
def factual_parse() -> ParseResult:
    """Clear factual query: ibuprofen contraindications."""
    return _parse(
        query="What are the contraindications for ibuprofen?",
        operation="lookup",
        entities=["ibuprofen"],
        confidence=0.95,
    )


@pytest.fixture
def ambiguous_parse() -> ParseResult:
    """Ambiguous / vague query."""
    return _parse(
        query="Tell me about it",
        operation="unsupported",
        entities=[],
        confidence=0.2,
    )


@pytest.fixture
def tabular_parse() -> ParseResult:
    """Tabular dosage table query."""
    return _parse(
        query="Show me the dosage table for aspirin",
        operation="lookup",
        entities=["aspirin"],
        confidence=0.9,
    )


@pytest.fixture
def keyword_parse() -> ParseResult:
    """List / keyword-oriented query."""
    return _parse(
        query="list all drug interactions",
        operation="list",
        entities=["drug interactions"],
        confidence=0.9,
    )


@pytest.fixture
def multi_intent_parse() -> ParseResult:
    """Multi-intent compare + list signals."""
    return _parse(
        query="compare and list the side effects of aspirin versus ibuprofen",
        operation="compare",
        entities=["aspirin", "ibuprofen"],
        confidence=0.85,
    )


@pytest.fixture
def empty_parse() -> ParseResult:
    """Empty / whitespace-only query."""
    return _parse(
        query="   ",
        operation="unsupported",
        entities=[],
        confidence=0.0,
    )


@pytest.fixture
def generic_config() -> RetrievalPlannerConfig:
    return RetrievalPlannerConfig()
