"""Regression / baseline scaffolding for unified quality gate."""

from __future__ import annotations

import json
from pathlib import Path


def test_pipeline_regression_scaffold(tmp_path: Path):
    baseline = {"pass_rate": 0.9, "total": 10, "passed": 9}
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["pass_rate"] >= 0.85
