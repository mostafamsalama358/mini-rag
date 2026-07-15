"""Unit tests for Answer Quality domain models."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from core.answer_quality.models import (
    CompletenessResult,
    CoverageResult,
    EvaluationResult,
    FaithfulnessResult,
    GoldenTestFixture,
    GoldenTestResult,
    RegressionDiff,
    ScoreThresholds,
)


def test_golden_fixture_optional_fields_default_to_none() -> None:
    fixture = GoldenTestFixture(question_id="q001", question="What dose?")
    assert fixture.expected_source_ids is None
    assert fixture.expected_answer_facets is None
    assert fixture.thresholds is None


def test_evaluation_result_serialises_to_valid_json() -> None:
    result = EvaluationResult(
        run_id="run-001",
        run_at="2026-07-15T09:00:00Z",
        aggregate_pass_rate=1.0,
        passed=True,
        question_results=[
            GoldenTestResult(
                question_id="q001",
                question="Test?",
                plan_id="plan_test001",
                coverage=CoverageResult(
                    question_id="q001",
                    coverage_score=1.0,
                    passed=True,
                ),
                faithfulness=FaithfulnessResult(
                    question_id="q001",
                    faithfulness_score=1.0,
                    passed=True,
                ),
                completeness=CompletenessResult(
                    question_id="q001",
                    completeness_score=1.0,
                    passed=True,
                ),
                passed=True,
                evaluated_at="2026-07-15T09:00:01Z",
            )
        ],
    )
    payload = json.loads(result.model_dump_json())
    assert payload["schema_version"] == "1.0.0"
    assert payload["passed"] is True


def test_score_thresholds_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        ScoreThresholds(coverage=1.5)


def test_golden_test_result_passed_requires_all_dimensions() -> None:
    result = GoldenTestResult(
        question_id="q001",
        question="Test?",
        plan_id="plan_test001",
        coverage=CoverageResult(question_id="q001", coverage_score=1.0, passed=True),
        faithfulness=FaithfulnessResult(
            question_id="q001",
            faithfulness_score=0.5,
            passed=False,
        ),
        completeness=CompletenessResult(
            question_id="q001",
            completeness_score=1.0,
            passed=True,
        ),
        passed=False,
        evaluated_at="2026-07-15T09:00:01Z",
    )
    assert result.passed is False


def test_regression_diff_has_regressions() -> None:
    diff = RegressionDiff(
        run_id_baseline="run-a",
        run_id_current="run-b",
        has_regressions=True,
    )
    assert diff.has_regressions is True
