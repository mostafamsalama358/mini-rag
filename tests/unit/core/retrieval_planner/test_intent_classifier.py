"""Tests for RuleBasedIntentClassifier."""

from __future__ import annotations

import pytest

from core.query_parser.schema import ParseResult, QueryPlan
from core.retrieval_planner.intent.rule_based import RuleBasedIntentClassifier
from core.retrieval_planner.models import RetrievalPlannerConfig


def _pr(query: str, operation: str, confidence: float = 0.9) -> ParseResult:
    return ParseResult(
        original_query=query,
        canonical_query=query,
        query_plan=QueryPlan(
            field="general",
            operation=operation,  # type: ignore[arg-type]
            scope="all",
            language="en",
            confidence=confidence,
        ),
        used_llm=False,
        latency_ms=1.0,
    )


@pytest.fixture
def classifier() -> RuleBasedIntentClassifier:
    return RuleBasedIntentClassifier()


@pytest.fixture
def config() -> RetrievalPlannerConfig:
    return RetrievalPlannerConfig()


@pytest.mark.parametrize(
    "operation,expected",
    [
        ("lookup", "factual"),
        ("list", "list"),
        ("compare", "comparative"),
        ("explain", "procedural"),
        ("count", "factual"),
    ],
)
def test_operation_mapping(classifier, config, operation, expected):
    intent = classifier.classify(_pr(f"query for {operation}", operation), config)
    assert intent.category == expected
    assert intent.confidence == 1.0


def test_tabular_pattern_override(classifier, config):
    intent = classifier.classify(
        _pr("Show me the dosage table for aspirin", "lookup"), config
    )
    assert intent.category == "tabular"
    assert intent.confidence == 0.8


def test_procedural_pattern(classifier, config):
    intent = classifier.classify(
        _pr("how to administer ibuprofen", "lookup"), config
    )
    assert intent.category == "procedural"
    assert intent.confidence == 0.8


def test_comparative_pattern(classifier, config):
    intent = classifier.classify(
        _pr("difference between aspirin and ibuprofen", "lookup"), config
    )
    assert intent.category == "comparative"
    assert intent.confidence == 0.8


def test_navigational_pattern(classifier, config):
    intent = classifier.classify(
        _pr("where is the dosage section", "lookup"), config
    )
    assert intent.category == "navigational"
    assert intent.confidence == 0.8


def test_unsupported_with_pattern(classifier, config):
    intent = classifier.classify(
        _pr("show the table of dosages", "unsupported"), config
    )
    assert intent.category == "tabular"
    assert intent.confidence == 0.6


def test_unsupported_no_pattern(classifier, config):
    intent = classifier.classify(_pr("xyzzy weird stuff", "unsupported"), config)
    assert intent.category == "factual"  # fallback
    assert intent.confidence == 0.4


def test_mixed_signals(classifier, config):
    intent = classifier.classify(
        _pr("compare and list side effects of aspirin versus ibuprofen", "compare"),
        config,
    )
    # Multiple distinct signals → mixed or comparative from pass1; mixed if multi-signal
    assert intent.category in ("mixed", "comparative")


def test_classifier_id(classifier):
    assert classifier.classifier_id == "rule_based"


def test_evidence_populated(classifier, config):
    intent = classifier.classify(
        _pr("Show me the dosage table for aspirin", "lookup"), config
    )
    assert len(intent.evidence) >= 1
