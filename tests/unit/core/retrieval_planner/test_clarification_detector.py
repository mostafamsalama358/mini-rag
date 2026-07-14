"""Tests for ConfidenceBasedClarificationDetector."""

from __future__ import annotations

import pytest

from core.query_parser.schema import ParseResult, QueryPlan
from core.retrieval_planner.clarification.confidence_based import (
    ConfidenceBasedClarificationDetector,
)
from core.retrieval_planner.models import QueryIntent, RetrievalPlannerConfig


@pytest.fixture
def detector() -> ConfidenceBasedClarificationDetector:
    return ConfidenceBasedClarificationDetector()


def _pr(
    *,
    query: str = "q",
    confidence: float = 0.9,
    needs_clarification: bool = False,
    clarification_prompt: str | None = None,
    operation: str = "lookup",
) -> ParseResult:
    return ParseResult(
        original_query=query,
        canonical_query=query,
        query_plan=QueryPlan(
            field="general",
            operation=operation,  # type: ignore[arg-type]
            scope="all",
            language="en",
            confidence=confidence,
            needs_clarification=needs_clarification,
            clarification_prompt=clarification_prompt,
        ),
        used_llm=False,
        latency_ms=1.0,
    )


def test_upstream_clarification_propagates(detector):
    cfg = RetrievalPlannerConfig()
    intent = QueryIntent(category="factual", confidence=0.9)
    required, question = detector.detect(
        _pr(
            needs_clarification=True,
            clarification_prompt="Which drug do you mean?",
        ),
        intent,
        cfg,
    )
    assert required is True
    assert question == "Which drug do you mean?"


def test_low_confidence_triggers_with_secondary(detector):
    cfg = RetrievalPlannerConfig(clarification_confidence_threshold=0.5)
    intent = QueryIntent(
        category="factual",
        confidence=0.3,
        secondary_categories=("list", "comparative"),
    )
    required, question = detector.detect(_pr(confidence=0.3), intent, cfg)
    assert required is True
    assert question is not None
    assert "list" in question or "comparative" in question


def test_empty_query_triggers(detector, empty_parse):
    cfg = RetrievalPlannerConfig()
    intent = QueryIntent(category="factual", confidence=0.9)
    required, question = detector.detect(empty_parse, intent, cfg)
    assert required is True
    assert question is not None
    assert len(question) > 0


def test_clear_query_does_not_trigger(detector, factual_parse):
    """≥ 85% precision guard — clear queries must not be blocked (SC-005)."""
    cfg = RetrievalPlannerConfig(clarification_confidence_threshold=0.5)
    intent = QueryIntent(category="factual", confidence=1.0)
    required, question = detector.detect(factual_parse, intent, cfg)
    assert required is False
    assert question is None


def test_detector_id(detector):
    assert detector.detector_id == "confidence_based"
