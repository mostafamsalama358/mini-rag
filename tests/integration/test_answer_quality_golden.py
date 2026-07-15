"""Integration tests for the Answer Quality golden test runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.answer_quality.registry import AnswerQualityRegistry
from tests.fixtures.answer_quality.snapshot_helpers import degrade_coverage, save_snapshot
from tests.unit.core.answer_quality.conftest import (
    build_answer_result,
    build_context,
    build_evidence_pack,
    default_config,
)
from core.answer_quality.models import PipelineSnapshot

FIXTURE_PATH = Path("tests/fixtures/answer_quality/generic_golden.yaml")
SNAPSHOT_DIR = Path("tests/fixtures/answer_quality/snapshots")


def _ensure_snapshots() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = [
        PipelineSnapshot(
            question_id="q001",
            answer_result=build_answer_result(
                answer="The adult dose is 325 mg every 4 to 6 hours."
            ),
            context=build_context(
                block_texts=["Adults: 325 mg every 4 to 6 hours."]
            ),
            evidence_pack=build_evidence_pack(["doc-aspirin-pil"]),
        ),
        PipelineSnapshot(
            question_id="q002",
            answer_result=build_answer_result(
                answer=(
                    "Avoid aspirin if allergic to aspirin or if you have "
                    "a bleeding disorder."
                )
            ),
            context=build_context(
                block_texts=[
                    "Contraindicated in patients allergic to aspirin.",
                    "Do not use with active bleeding disorder.",
                ]
            ),
            evidence_pack=build_evidence_pack(
                ["doc-aspirin-pil", "doc-bnf-aspirin"]
            ),
        ),
        PipelineSnapshot(
            question_id="q003",
            answer_result=build_answer_result(
                answer=(
                    "Aspirin is not recommended for children due to "
                    "risk of Reye's syndrome."
                )
            ),
            context=build_context(
                block_texts=[
                    "Aspirin is not recommended in paediatric patients.",
                    "Associated with Reye's syndrome in children.",
                ]
            ),
            evidence_pack=build_evidence_pack(["doc-paediatric-guidance"]),
        ),
    ]
    for snapshot in snapshots:
        target = SNAPSHOT_DIR / f"{snapshot.question_id}.json"
        if not target.exists():
            save_snapshot(snapshot, target)


@pytest.fixture(scope="module", autouse=True)
def _seed_snapshots() -> None:
    _ensure_snapshots()


@pytest.mark.asyncio
async def test_known_good_golden_run(default_config) -> None:
    fixtures = AnswerQualityRegistry.load_fixtures(FIXTURE_PATH)
    snapshots = AnswerQualityRegistry.load_snapshots(SNAPSHOT_DIR)
    runner = AnswerQualityRegistry.default_runner()

    result = await runner.run(
        fixtures,
        snapshots,
        default_config,
        fixture_file=str(FIXTURE_PATH),
    )

    assert result.passed is True
    assert result.aggregate_pass_rate >= 0.9
    result.model_dump_json()


@pytest.mark.asyncio
async def test_degraded_snapshot_fails(default_config) -> None:
    fixtures = AnswerQualityRegistry.load_fixtures(FIXTURE_PATH)
    snapshots = AnswerQualityRegistry.load_snapshots(SNAPSHOT_DIR)
    degraded = degrade_coverage(snapshots, question_id=fixtures[0].question_id)
    runner = AnswerQualityRegistry.default_runner()

    result = await runner.run(
        fixtures,
        degraded,
        default_config,
        fixture_file=str(FIXTURE_PATH),
    )

    q_result = next(
        item for item in result.question_results if item.question_id == fixtures[0].question_id
    )
    assert q_result.coverage.passed is False
    assert q_result.coverage.coverage_score is not None
    assert q_result.coverage.coverage_score < 0.7
    assert result.passed is False
