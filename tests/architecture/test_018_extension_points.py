"""T053 — each stage has ≥1 extension point; tighten-only rule stated."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, markdown_table_rows, read


STAGES = [
    "Query Understanding",
    "Retrieval Plan",
    "Retrieval",
    "Evidence",
    "Context",
    "Answer Generation",
]


def test_extension_points_per_stage_and_tighten_only() -> None:
    text = read(GOV_018 / "extension-points-registry.md")
    assert "tighten-only" in text.lower() or "tighten only" in text.lower()
    rows = markdown_table_rows(text)
    stages_seen = {row[0].strip() for row in rows[1:]}
    missing = [s for s in STAGES if s not in stages_seen]
    assert not missing, f"Stages missing extension points: {missing}"
    for stage in STAGES:
        count = sum(1 for row in rows[1:] if row[0].strip() == stage)
        assert count >= 1, f"{stage} needs ≥1 extension point"
