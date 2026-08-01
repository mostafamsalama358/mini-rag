"""T028 — required vignette themes from quickstart §2."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, read


REQUIRED_THEME_MARKERS = [
    "filter",
    "re-parse",
    "completeness",
    "conflict",
    "citation",
    "ungrounded",
]


def test_required_themes_documented() -> None:
    text = read(GOV_018 / "failure-vignette-catalog.md").lower()
    missing = [m for m in REQUIRED_THEME_MARKERS if m not in text]
    assert not missing, f"Missing theme markers: {missing}"
