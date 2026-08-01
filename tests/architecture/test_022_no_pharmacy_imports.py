"""022 — shared runtime must not import fields.pharmacy.*."""

from __future__ import annotations

import re

from tests.architecture._repo import REPO_ROOT

RUNTIME_ROOTS = (
    REPO_ROOT / "src" / "services" / "rag",
)

_STATIC_PHARMACY_IMPORT = re.compile(
    r"^\s*(?:from\s+fields\.pharmacy(?:\.\w+)*\s+import|import\s+fields\.pharmacy(?:\.\w+)*)",
    re.MULTILINE,
)


def test_runtime_packages_do_not_import_pharmacy_fields() -> None:
    hits: list[str] = []
    for root in RUNTIME_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if _STATIC_PHARMACY_IMPORT.search(text):
                hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, hits
