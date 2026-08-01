"""T043 — quality-architecture-review checklist has required MUST REJECT items."""

from __future__ import annotations

from tests.architecture._repo import CHECKLISTS_018, read


REQUIRED_PHRASES = [
    "parallel",
    "mega-stage",
    "coverage",
    "014",
    "runtime",
]


def test_quality_review_checklist_must_reject_items() -> None:
    text = read(CHECKLISTS_018 / "quality-architecture-review.md").lower()
    assert "must reject" in text
    missing = [p for p in REQUIRED_PHRASES if p not in text]
    assert not missing, f"Checklist missing phrases: {missing}"
    assert "answer" in text and "coverage" in text
