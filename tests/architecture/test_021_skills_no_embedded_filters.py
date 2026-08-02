"""021 — Skill YAML must not embed filters lists."""

from __future__ import annotations

import yaml

from tests.architecture._repo import REPO_ROOT

SKILL_DIRS = [
    REPO_ROOT / "src" / "fields" / "pharmacy" / "skills",
    REPO_ROOT / "src" / "fields" / "legal" / "skills",
    REPO_ROOT / "src" / "fields" / "grc" / "skills",
]


def test_skill_yaml_has_no_top_level_filters() -> None:
    checked = 0
    for skills_dir in SKILL_DIRS:
        if not skills_dir.is_dir():
            continue
        for path in skills_dir.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            assert "filters" not in data, f"{path} embeds filters"
            checked += 1
    assert checked > 0
