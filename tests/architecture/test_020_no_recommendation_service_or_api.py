"""T013 — no Recommendation Service/API; ADR-020-001 present."""

from __future__ import annotations

from pathlib import Path

from tests.architecture._repo import REPO_ROOT

GOV_020 = REPO_ROOT / "specs" / "020-pharmacy-recommendation" / "governance"
ROUTES = REPO_ROOT / "src" / "routes"


def test_adr_020_001_exists() -> None:
    path = GOV_020 / "adr-020-001-recommendation-as-capability.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "No Recommendation Service" in text or "no Recommendation Service" in text.lower() or "No Recommendation Service" in text
    assert "Capability" in text


def test_no_recommend_production_route_module() -> None:
    forbidden = list(ROUTES.rglob("*recommend*.py")) if ROUTES.is_dir() else []
    assert not forbidden, f"Unexpected recommend route modules: {forbidden}"
