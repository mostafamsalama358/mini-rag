"""T049 — frozen benchmarks cannot mutate in place."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, read


def test_benchmark_freeze_forbids_in_place_mutation() -> None:
    text = read(GOV_019 / "dataset-benchmark-governance-summary.md")
    assert "Frozen" in text
    assert "in-place" in text.lower() or "in place" in text.lower()
