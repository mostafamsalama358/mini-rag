"""T028 — planner-correct exclusions are not Engine Recall misses."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, read


def test_planner_constraint_exclusion_documented() -> None:
    text = read(GOV_019 / "metric-dependency-map.md")
    assert "out-of-scope" in text.lower() or "exclusions" in text.lower()
    assert "Recall" in text
    assert "Planner" in text or "Plan" in text
