"""T015 — 018 governance artifact presence."""

from __future__ import annotations

from tests.architecture._repo import GOV_018


REQUIRED_FILES = [
    "README.md",
    "stage-ownership-map.md",
    "continuity-contract-index.md",
    "quality-entity-catalog.md",
    "failure-vignette-catalog.md",
    "modularity-freeze.md",
    "relationship-to-014-017.md",
    "stage-quality-metrics.md",
    "quality-context-trace-registry.md",
    "extension-points-registry.md",
]


def test_018_governance_files_exist() -> None:
    missing = [name for name in REQUIRED_FILES if not (GOV_018 / name).is_file()]
    assert not missing, f"Missing 018 governance files: {missing}"
