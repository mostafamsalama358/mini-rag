"""T015 — 019 governance artifact presence."""

from __future__ import annotations

from tests.architecture._repo import GOV_019


REQUIRED_FILES = [
    "README.md",
    "metric-ownership-registry.md",
    "evaluation-profile-index.md",
    "evaluation-entity-catalog.md",
    "error-taxonomy-catalog.md",
    "evaluation-non-ownership-freeze.md",
    "relationship-to-014-018.md",
    "metric-dependency-map.md",
    "judge-layer-registry.md",
    "dataset-benchmark-governance-summary.md",
]


def test_019_governance_files_exist() -> None:
    missing = [name for name in REQUIRED_FILES if not (GOV_019 / name).is_file()]
    assert not missing, f"Missing 019 governance files: {missing}"
