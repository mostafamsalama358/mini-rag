"""T052 — Quality Context documents additive/namespaced rules; forbids upstream overwrite."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, read


def test_quality_context_overwrite_rules() -> None:
    text = read(GOV_018 / "quality-context-trace-registry.md").lower()
    assert "additive" in text or "namespaced" in text
    assert "overwrite" in text
    assert "forbidden" in text or "must not overwrite" in text or "c11" in text
