"""T044 — architecture-review checklist contains governance MUST items."""

from __future__ import annotations

from tests.architecture._repo import CHECKLISTS, read


REQUIRED_PHRASES = [
    "Single Owner",
    "ContractRole",
    "Dependency direction",
    "duplicate ownership",
    "parallel production",
    "Lifecycle",
    "ADR",
]


def test_architecture_review_has_governance_musts() -> None:
    text = read(CHECKLISTS / "architecture-review.md")
    assert "## MUST (Governance)" in text or "MUST (Governance)" in text
    missing = [p for p in REQUIRED_PHRASES if p.lower() not in text.lower()]
    assert not missing, f"Checklist missing phrases: {missing}"
