"""T036 — adversarial vignette themes present."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


def test_adversarial_themes_present() -> None:
    rows = markdown_table_rows(read(GOV_019 / "failure-vignette-catalog.md"))
    themes = " ".join(r[-1].lower() for r in rows[1:])
    assert "fabricated-entity" in themes
    assert "mismatched-citation" in themes
    assert "correct-no-answer" in themes
