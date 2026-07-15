"""Unit tests for JsonRegressionStore."""

from __future__ import annotations

import json

import pytest

from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.errors import RunNotFoundError
from core.answer_quality.models import (
    CompletenessResult,
    CoverageResult,
    EvaluationResult,
    FaithfulnessResult,
    GoldenTestResult,
)
from core.answer_quality.regression.store import JsonRegressionStore


def _evaluation_result(
    *,
    run_id: str,
    run_at: str,
    coverage_score: float = 1.0,
) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        run_at=run_at,
        aggregate_pass_rate=1.0,
        passed=True,
        question_results=[
            GoldenTestResult(
                question_id="q001",
                question="Test?",
                plan_id="plan_test001",
                coverage=CoverageResult(
                    question_id="q001",
                    coverage_score=coverage_score,
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
                evaluated_at=run_at,
            )
        ],
    )


@pytest.mark.asyncio
async def test_save_and_load_round_trip(tmp_path) -> None:
    store = JsonRegressionStore(run_store_dir=tmp_path)
    config = AnswerQualityConfig(run_store_dir=str(tmp_path))
    original = _evaluation_result(run_id="run-a", run_at="2026-07-15T09:00:00Z")

    await store.save(original)
    loaded = await store.load("run-a")

    assert json.loads(loaded.model_dump_json()) == json.loads(original.model_dump_json())
    assert loaded.run_id == "run-a"


@pytest.mark.asyncio
async def test_list_runs_sorted_by_run_at(tmp_path) -> None:
    store = JsonRegressionStore(run_store_dir=tmp_path)
    await store.save(_evaluation_result(run_id="run-b", run_at="2026-07-16T09:00:00Z"))
    await store.save(_evaluation_result(run_id="run-a", run_at="2026-07-15T09:00:00Z"))

    run_ids = await store.list_runs()

    assert run_ids == ["run-a", "run-b"]


@pytest.mark.asyncio
async def test_diff_detects_coverage_regression(tmp_path) -> None:
    store = JsonRegressionStore(run_store_dir=tmp_path)
    config = AnswerQualityConfig(run_store_dir=str(tmp_path))
    await store.save(_evaluation_result(run_id="run-a", run_at="2026-07-15T09:00:00Z", coverage_score=1.0))
    await store.save(_evaluation_result(run_id="run-b", run_at="2026-07-16T09:00:00Z", coverage_score=0.5))

    diff = await store.diff("run-a", "run-b", config)

    assert diff.has_regressions is True


@pytest.mark.asyncio
async def test_diff_raises_for_unknown_run(tmp_path) -> None:
    store = JsonRegressionStore(run_store_dir=tmp_path)
    config = AnswerQualityConfig(run_store_dir=str(tmp_path))

    with pytest.raises(RunNotFoundError):
        await store.diff("missing-a", "missing-b", config)


@pytest.mark.asyncio
async def test_resave_same_run_id_overwrites(tmp_path) -> None:
    store = JsonRegressionStore(run_store_dir=tmp_path)
    first = _evaluation_result(run_id="run-a", run_at="2026-07-15T09:00:00Z", coverage_score=1.0)
    second = _evaluation_result(run_id="run-a", run_at="2026-07-15T10:00:00Z", coverage_score=0.5)

    await store.save(first)
    await store.save(second)
    loaded = await store.load("run-a")

    assert loaded.run_at == "2026-07-15T10:00:00Z"
    assert loaded.question_results[0].coverage.coverage_score == pytest.approx(0.5)
