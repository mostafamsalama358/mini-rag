"""T055 — RecommendEvalCase golden schema."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = (
    ROOT
    / "specs"
    / "020-pharmacy-recommendation"
    / "eval"
    / "recommend_golden_v1.jsonl"
)

REQUIRED_KEYS = {"id", "query", "language", "expect"}


def test_golden_file_exists_and_parses() -> None:
    assert GOLDEN.is_file()
    rows = []
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    assert len(rows) >= 10
    for row in rows:
        assert REQUIRED_KEYS <= set(row.keys())
