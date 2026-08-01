"""T035 — judges must not invent parallel metric names."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, read


def test_judge_metric_stability_rule() -> None:
    text = read(GOV_019 / "judge-layer-registry.md")
    assert "Rule Judge" in text
    assert "LLM Judge" in text
    assert "Human Judge" in text
    assert "Hybrid Judge" in text
    assert "parallel metric" in text.lower() or "MUST NOT redefine" in text
