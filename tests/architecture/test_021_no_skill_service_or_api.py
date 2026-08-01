"""021 — no Skill Service/API; ADR-021-001 present."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT

GOV_021 = REPO_ROOT / "specs" / "021-domain-skill-framework" / "governance"
ROUTES = REPO_ROOT / "src" / "routes"


def test_adr_021_001_exists() -> None:
    path = GOV_021 / "adr-021-001-skills-as-domain-pack-capability.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Capability" in text
    assert "Skill" in text


def test_no_skill_production_route_module() -> None:
    forbidden = list(ROUTES.rglob("*skill*.py")) if ROUTES.is_dir() else []
    assert not forbidden, f"Unexpected skill route modules: {forbidden}"
