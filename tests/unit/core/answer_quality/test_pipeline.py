"""Unit tests for GoldenTestRunner and regression tracking."""

from __future__ import annotations

import json

import pytest

from core.answer_quality.completeness.scorer import KeywordCompletenessScorer
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.coverage.evaluator import DocIdCoverageEvaluator
from core.answer_quality.errors import EvaluationError, UnmatchedQuestionError
from core.answer_quality.faithfulness.scorer import TextFaithfulnessScorer
from core.answer_quality.models import (
    CompletenessResult,
    CoverageResult,
    EvaluationResult,
    FaithfulnessResult,
    GoldenTestResult,
    PipelineSnapshot,
)
from core.answer_quality.pipeline import GoldenTestRunner
from core.answer_quality.regression.store import JsonRegressionStore
from tests.unit.core.answer_quality.conftest import (
    build_answer_result,
    build_context,
    build_evidence_pack,
    build_golden_fixture,
    default_config,
)


def _runner() -> GoldenTestRunner:
    return GoldenTestRunner(
        coverage_evaluator=DocIdCoverageEvaluator(),
        faithfulness_scorer=TextFaithfulnessScorer(),
        completeness_scorer=KeywordCompletenessScorer(),
    )


def _snapshot(
    question_id: str,
    *,
    doc_ids: list[str] | None = None,
    answer: str = "Take 325 mg every 4 hours.",
    block_texts: list[str] | None = None,
) -> PipelineSnapshot:
    return PipelineSnapshot(
        question_id=question_id,
        answer_result=build_answer_result(answer=answer),
        context=build_context(
            block_texts=block_texts or ["The standard dose is 325 mg every 4 hours."]
        ),
        evidence_pack=build_evidence_pack(doc_ids or ["doc-a"]),
    )


@pytest.mark.asyncio
async def test_known_good_snapshot_set_passes(default_config) -> None:
    fixtures = [
        build_golden_fixture(
            "q001",
            expected_source_ids=["doc-a"],
            expected_answer_facets=["325 mg"],
        )
    ]
    snapshots = [_snapshot("q001", doc_ids=["doc-a"])]

    result = await _runner().run(fixtures, snapshots, default_config)

    assert result.passed is True
    assert result.aggregate_pass_rate == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_missing_source_fails(default_config) -> None:
    fixtures = [build_golden_fixture("q001", expected_source_ids=["doc-a", "doc-b"])]
    snapshots = [_snapshot("q001", doc_ids=["doc-a"])]

    result = await _runner().run(fixtures, snapshots, default_config)

    assert result.passed is False
    assert result.question_results[0].coverage.passed is False


@pytest.mark.asyncio
async def test_empty_fixtures_raises(default_config) -> None:
    with pytest.raises(EvaluationError, match="No fixtures"):
        await _runner().run([], [], default_config)


@pytest.mark.asyncio
async def test_unmatched_question_raises(default_config) -> None:
    fixtures = [build_golden_fixture("q001", expected_source_ids=["doc-a"])]
    snapshots = [_snapshot("q002")]

    with pytest.raises(UnmatchedQuestionError):
        await _runner().run(fixtures, snapshots, default_config)


@pytest.mark.asyncio
async def test_evaluation_result_json_serialisable(default_config) -> None:
    fixtures = [build_golden_fixture("q001", expected_source_ids=["doc-a"])]
    snapshots = [_snapshot("q001", doc_ids=["doc-a"])]

    result = await _runner().run(fixtures, snapshots, default_config)
    payload = json.loads(result.model_dump_json())
    assert payload["aggregate_pass_rate"] == pytest.approx(1.0)


def _build_evaluation_result(
    *,
    run_id: str,
    coverage_score: float,
    question_id: str = "q001",
) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        run_at="2026-07-15T09:00:00Z",
        aggregate_pass_rate=1.0 if coverage_score >= 0.8 else 0.0,
        passed=coverage_score >= 0.8,
        question_results=[
            GoldenTestResult(
                question_id=question_id,
                question="Test?",
                plan_id="plan_test001",
                coverage=CoverageResult(
                    question_id=question_id,
                    coverage_score=coverage_score,
                    passed=coverage_score >= 0.8,
                ),
                faithfulness=FaithfulnessResult(
                    question_id=question_id,
                    faithfulness_score=1.0,
                    passed=True,
                ),
                completeness=CompletenessResult(
                    question_id=question_id,
                    completeness_score=1.0,
                    passed=True,
                ),
                passed=coverage_score >= 0.8,
                evaluated_at="2026-07-15T09:00:01Z",
            )
        ],
    )


@pytest.mark.asyncio
async def test_regression_diff_detects_drop(tmp_path) -> None:
    store = JsonRegressionStore(run_store_dir=tmp_path)
    config = AnswerQualityConfig(run_store_dir=str(tmp_path))

    result_a = _build_evaluation_result(run_id="run-a", coverage_score=1.0)
    result_b = _build_evaluation_result(run_id="run-b", coverage_score=0.5)

    await store.save(result_a)
    await store.save(result_b)

    diff = await store.diff("run-a", "run-b", config)

    assert diff.has_regressions is True
    assert any(
        delta.dimension == "coverage" and delta.delta is not None and delta.delta < -0.3
        for delta in diff.regressions
    )
    assert not diff.improvements
