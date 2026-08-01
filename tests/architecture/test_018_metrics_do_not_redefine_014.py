"""T034 — stage metrics must not redefine 014 goldens; 014 authority stated."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, read


def test_014_authority_and_non_redefinition() -> None:
    text = read(GOV_018 / "stage-quality-metrics.md").lower()
    assert "014" in text
    assert "authority" in text
    assert "do not redefine" in text or "does not redefine" in text or "not redefine" in text
    for metric in ("coverage", "faithfulness", "completeness"):
        assert metric in text
