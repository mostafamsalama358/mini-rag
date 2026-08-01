"""T045 — AP1–AP14 covered in review checklist or antipattern index."""

from __future__ import annotations

from tests.architecture.test_forbidden_patterns_documented import (
    test_ap1_through_ap14_listed,
)


def test_antipattern_coverage() -> None:
    test_ap1_through_ap14_listed()
