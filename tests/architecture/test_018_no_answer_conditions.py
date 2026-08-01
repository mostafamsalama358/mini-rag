"""T036 — all seven no-answer conditions from spec §15 are cataloged."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, read


CONDITIONS = [
    "no_evidence",
    "weak_evidence",
    "conflicting_evidence",
    "partial_evidence",
    "ambiguous_query",
    "out_of_domain",
    "restricted_answer",
]


def test_no_answer_conditions_present() -> None:
    text = read(GOV_018 / "no-answer-decision-catalog.md")
    missing = [c for c in CONDITIONS if c not in text]
    assert not missing, f"Missing conditions: {missing}"
