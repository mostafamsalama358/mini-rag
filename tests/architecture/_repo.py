"""Helpers to locate 016/018/019 governance artifacts from the repo root."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOV = REPO_ROOT / "specs" / "016-architecture-consolidation" / "governance"
CHECKLISTS = REPO_ROOT / "specs" / "016-architecture-consolidation" / "checklists"
SPEC = REPO_ROOT / "specs" / "016-architecture-consolidation" / "spec.md"
GOV_018 = REPO_ROOT / "specs" / "018-rag-quality-architecture" / "governance"
CHECKLISTS_018 = REPO_ROOT / "specs" / "018-rag-quality-architecture" / "checklists"
SPEC_018 = REPO_ROOT / "specs" / "018-rag-quality-architecture" / "spec.md"
CONTRACTS_018 = REPO_ROOT / "specs" / "018-rag-quality-architecture" / "contracts"
DATA_MODEL_018 = REPO_ROOT / "specs" / "018-rag-quality-architecture" / "data-model.md"
GOV_019 = REPO_ROOT / "specs" / "019-rag-evaluation-framework" / "governance"
CHECKLISTS_019 = REPO_ROOT / "specs" / "019-rag-evaluation-framework" / "checklists"
SPEC_019 = REPO_ROOT / "specs" / "019-rag-evaluation-framework" / "spec.md"
CONTRACTS_019 = REPO_ROOT / "specs" / "019-rag-evaluation-framework" / "contracts"
DATA_MODEL_019 = REPO_ROOT / "specs" / "019-rag-evaluation-framework" / "data-model.md"
AGENTS = REPO_ROOT / "AGENTS.md"
ARCHITECTURE = REPO_ROOT / "src" / "ARCHITECTURE.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def markdown_table_rows(text: str) -> list[list[str]]:
    """Parse GitHub-style markdown tables; return data rows (cells stripped)."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(set(c) <= {"-", ":"} for c in cells):
            continue
        rows.append(cells)
    return rows
