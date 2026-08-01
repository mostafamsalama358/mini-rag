"""T043 — re-parse documented as planner failure citing 018 authority."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, read


def test_planner_reparse_rule() -> None:
    text = read(GOV_019 / "planner-evaluation-notes.md")
    assert "re-parse" in text.lower() or "Re-interpret" in text or "re-interpret" in text.lower()
    assert "018" in text
    assert "Understood Query" in text
