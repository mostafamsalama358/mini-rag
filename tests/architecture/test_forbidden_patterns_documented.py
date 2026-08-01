"""T038 / T045 helpers — AP5 and AP1–AP14 documented."""

from __future__ import annotations

from tests.architecture._repo import CHECKLISTS, GOV, read


def test_ap5_mentioned_in_antipattern_index() -> None:
    text = read(GOV / "antipattern-index.md")
    assert "AP5" in text
    assert "Composition" in text or "composition" in text.lower()


def test_ap1_through_ap14_listed() -> None:
    combined = read(GOV / "antipattern-index.md") + read(
        CHECKLISTS / "architecture-review.md"
    )
    missing = [f"AP{i}" for i in range(1, 15) if f"AP{i}" not in combined]
    assert not missing, f"Missing anti-pattern ids: {missing}"
