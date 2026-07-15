"""Snapshot serialisation helpers for Answer Quality integration tests."""

from __future__ import annotations

from pathlib import Path

from core.answer_quality.models import PipelineSnapshot, PipelineSnapshotRecord
from tests.unit.core.answer_quality.conftest import build_evidence_pack


def save_snapshot(snapshot: PipelineSnapshot, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = PipelineSnapshotRecord.from_snapshot(snapshot)
    target.write_text(record.model_dump_json(), encoding="utf-8")


def load_snapshot(path: str | Path) -> PipelineSnapshot:
    record = PipelineSnapshotRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
    return record.to_snapshot()


def degrade_coverage(
    snapshots: list[PipelineSnapshot],
    question_id: str,
) -> list[PipelineSnapshot]:
    degraded: list[PipelineSnapshot] = []
    for snapshot in snapshots:
        if snapshot.question_id != question_id:
            degraded.append(snapshot)
            continue
        degraded.append(
            PipelineSnapshot(
                question_id=snapshot.question_id,
                answer_result=snapshot.answer_result,
                context=snapshot.context,
                evidence_pack=build_evidence_pack([]),
            )
        )
    return degraded
