"""022 — shared runtime must not branch on hardcoded domain field names."""

from __future__ import annotations

import re

from tests.architecture._repo import REPO_ROOT

SCAN_ROOTS = (
    REPO_ROOT / "src" / "services" / "rag" / "answer_service.py",
    REPO_ROOT / "src" / "services" / "rag" / "pipeline",
    REPO_ROOT / "src" / "services" / "rag" / "skills",
)

DOMAIN_FIELD_PATTERNS = (
    re.compile(r"""field\s*==\s*["']interactions["']"""),
    re.compile(r"""query_plan\.field\s*==\s*["']interactions["']"""),
    re.compile(r"""\.field\s*==\s*["']dosage["']"""),
    re.compile(r"""\.field\s*==\s*["']leaflet["']"""),
)


def test_no_domain_field_control_flow() -> None:
    hits: list[str] = []
    for root in SCAN_ROOTS:
        paths = [root] if root.is_file() else root.rglob("*.py")
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in DOMAIN_FIELD_PATTERNS:
                if pattern.search(text):
                    hits.append(f"{path.relative_to(REPO_ROOT)}: {pattern.pattern}")
    assert not hits, hits
