"""Golden test runner orchestrating all quality scorers."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.errors import EvaluationError, UnmatchedQuestionError
from core.answer_quality.interfaces import (
    ICompletenessScorer,
    ICoverageEvaluator,
    IFaithfulnessScorer,
    IGoldenTestRunner,
)
from core.answer_quality.models import (
    EvaluationResult,
    GoldenTestResult,
    PipelineSnapshot,
    GoldenTestFixture,
)

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


class GoldenTestRunner(IGoldenTestRunner):
    def __init__(
        self,
        coverage_evaluator: ICoverageEvaluator,
        faithfulness_scorer: IFaithfulnessScorer,
        completeness_scorer: ICompletenessScorer,
    ) -> None:
        self._coverage = coverage_evaluator
        self._faithfulness = faithfulness_scorer
        self._completeness = completeness_scorer

    async def run(
        self,
        fixtures: list[GoldenTestFixture],
        pipeline_outputs: list[PipelineSnapshot],
        config: AnswerQualityConfig,
        *,
        fixture_file: str = "",
    ) -> EvaluationResult:
        if not fixtures:
            raise EvaluationError("No fixtures provided")

        snapshot_by_id = {snapshot.question_id: snapshot for snapshot in pipeline_outputs}
        run_id = uuid.uuid4().hex[:8]
        run_at = _utc_now_iso()
        question_results: list[GoldenTestResult] = []

        for fixture in fixtures:
            snapshot = snapshot_by_id.get(fixture.question_id)
            if snapshot is None:
                raise UnmatchedQuestionError(
                    f"No pipeline snapshot for question_id={fixture.question_id!r}"
                )

            coverage_task = self._coverage.evaluate(
                fixture, snapshot.evidence_pack, config
            )
            faithfulness_task = self._faithfulness.score(
                fixture, snapshot.answer_result, snapshot.context, config
            )
            completeness_task = self._completeness.score(
                fixture, snapshot.answer_result, config
            )
            coverage, faithfulness, completeness = await asyncio.gather(
                coverage_task,
                faithfulness_task,
                completeness_task,
            )

            if snapshot.answer_result.no_answer:
                logger.warning(
                    "no_answer recorded",
                    extra={
                        "run_id": run_id,
                        "question_id": fixture.question_id,
                        "no_answer": True,
                    },
                )

            conflict_ok = True
            if snapshot.context.conflicts:
                conflict_ok = bool(snapshot.answer_result.conflicts_disclosed)
                if not conflict_ok:
                    logger.warning(
                        "conflict_disclosure_missing",
                        extra={
                            "run_id": run_id,
                            "question_id": fixture.question_id,
                            "conflict_count": len(snapshot.context.conflicts),
                        },
                    )

            passed = (
                coverage.passed
                and faithfulness.passed
                and completeness.passed
                and conflict_ok
            )
            evaluated_at = _utc_now_iso()
            question_results.append(
                GoldenTestResult(
                    question_id=fixture.question_id,
                    question=fixture.question,
                    plan_id=snapshot.answer_result.plan_id,
                    coverage=coverage,
                    faithfulness=faithfulness,
                    completeness=completeness,
                    passed=passed,
                    evaluated_at=evaluated_at,
                )
            )

            log_extra = {
                "run_id": run_id,
                "question_id": fixture.question_id,
                "coverage_score": coverage.coverage_score,
                "faithfulness_score": faithfulness.faithfulness_score,
                "completeness_score": completeness.completeness_score,
                "passed": passed,
            }
            if passed:
                logger.info("golden test question evaluated", extra=log_extra)
            else:
                logger.warning(
                    "golden test question failed",
                    extra={
                        **log_extra,
                        "missing_source_ids": coverage.missing_source_ids,
                        "unsupported_claims": faithfulness.unsupported_claims,
                        "uncovered_facets": completeness.uncovered_facets,
                    },
                )

        passed_count = sum(1 for result in question_results if result.passed)
        aggregate_pass_rate = passed_count / len(question_results)

        coverage_scores = [
            result.coverage.coverage_score
            for result in question_results
            if result.coverage.coverage_score is not None
        ]
        faithfulness_scores = [
            result.faithfulness.faithfulness_score
            for result in question_results
            if result.faithfulness.faithfulness_score is not None
        ]
        completeness_scores = [
            result.completeness.completeness_score
            for result in question_results
            if result.completeness.completeness_score is not None
        ]

        return EvaluationResult(
            run_id=run_id,
            run_at=run_at,
            question_results=question_results,
            aggregate_pass_rate=aggregate_pass_rate,
            aggregate_coverage=_mean(coverage_scores),
            aggregate_faithfulness=_mean(faithfulness_scores),
            aggregate_completeness=_mean(completeness_scores),
            passed=aggregate_pass_rate >= config.pass_rate_threshold,
            fixture_file=fixture_file,
        )
