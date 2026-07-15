"""Factory and wiring for Answer Quality components."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml

from core.answer_quality.completeness.scorer import KeywordCompletenessScorer
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.coverage.evaluator import DocIdCoverageEvaluator
from core.answer_quality.errors import (
    EvaluationError,
    FixtureLoadError,
    UnmatchedQuestionError,
)
from core.answer_quality.faithfulness.scorer import TextFaithfulnessScorer
from core.answer_quality.models import GoldenTestFixture, PipelineSnapshot, PipelineSnapshotRecord
from core.answer_quality.pipeline import GoldenTestRunner


class AnswerQualityRegistry:
    @staticmethod
    def default_runner() -> GoldenTestRunner:
        return GoldenTestRunner(
            coverage_evaluator=DocIdCoverageEvaluator(),
            faithfulness_scorer=TextFaithfulnessScorer(),
            completeness_scorer=KeywordCompletenessScorer(),
        )

    @staticmethod
    def load_fixtures(path: str | Path) -> list[GoldenTestFixture]:
        fixture_path = Path(path)
        try:
            with fixture_path.open("r", encoding="utf-8") as handle:
                data: dict[str, Any] = yaml.safe_load(handle) or {}
        except OSError as exc:
            raise FixtureLoadError(f"Cannot read fixture file: {fixture_path}") from exc

        raw_fixtures = data.get("fixtures")
        if not isinstance(raw_fixtures, list):
            raise FixtureLoadError("Fixture file must contain a 'fixtures' list")

        fixtures: list[GoldenTestFixture] = []
        for index, item in enumerate(raw_fixtures):
            try:
                fixtures.append(GoldenTestFixture.model_validate(item))
            except Exception as exc:
                raise FixtureLoadError(
                    f"Invalid fixture at index {index} in {fixture_path}"
                ) from exc
        return fixtures

    @staticmethod
    def load_snapshots(path: str | Path) -> list[PipelineSnapshot]:
        snapshot_dir = Path(path)
        if not snapshot_dir.exists():
            raise FixtureLoadError(f"Snapshot directory not found: {snapshot_dir}")

        snapshots: list[PipelineSnapshot] = []
        for snapshot_path in sorted(snapshot_dir.glob("*.json")):
            try:
                snapshots.append(
                    PipelineSnapshotRecord.model_validate_json(
                        snapshot_path.read_text(encoding="utf-8")
                    ).to_snapshot()
                )
            except Exception as exc:
                raise FixtureLoadError(
                    f"Invalid snapshot file: {snapshot_path}"
                ) from exc
        return snapshots

    @staticmethod
    def run_and_exit(
        fixtures: list[GoldenTestFixture],
        snapshots: list[PipelineSnapshot],
        config: AnswerQualityConfig,
        *,
        fixture_file: str = "",
    ) -> None:
        runner = AnswerQualityRegistry.default_runner()
        try:
            result = asyncio.run(
                runner.run(
                    fixtures,
                    snapshots,
                    config,
                    fixture_file=fixture_file,
                )
            )
        except (EvaluationError, UnmatchedQuestionError, FixtureLoadError) as exc:
            raise SystemExit(2) from exc

        if result.passed:
            raise SystemExit(0)
        raise SystemExit(1)
