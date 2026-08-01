#!/usr/bin/env python3
"""Aggregate shadow JSONL reports into divergence summaries."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def aggregate(shadow_dir: Path) -> dict:
    by_stage: Counter[str] = Counter()
    by_project: dict[str, dict] = defaultdict(lambda: {"total": 0, "diverged": 0})
    total = 0
    diverged = 0
    similarities: list[float] = []

    for path in sorted(shadow_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            total += 1
            project_id = str(row.get("project_id", "unknown"))
            by_project[project_id]["total"] += 1
            if row.get("diverged"):
                diverged += 1
                by_project[project_id]["diverged"] += 1
                stage = row.get("first_divergent_stage") or "unknown"
                by_stage[stage] += 1
            sim = row.get("answer_similarity")
            if isinstance(sim, (int, float)):
                similarities.append(float(sim))

    median_sim = None
    if similarities:
        ordered = sorted(similarities)
        mid = len(ordered) // 2
        median_sim = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2

    return {
        "total_records": total,
        "diverged": diverged,
        "divergence_rate": (diverged / total) if total else 0.0,
        "median_answer_similarity": median_sim,
        "first_divergent_stage_counts": dict(by_stage),
        "by_project": dict(by_project),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shadow-dir", type=Path, default=Path(".rag_shadow"))
    parser.add_argument("--out", type=Path, default=Path("eval_run/shadow_aggregate.json"))
    args = parser.parse_args()
    if not args.shadow_dir.exists():
        summary = {
            "total_records": 0,
            "diverged": 0,
            "divergence_rate": 0.0,
            "median_answer_similarity": None,
            "first_divergent_stage_counts": {},
            "by_project": {},
        }
    else:
        summary = aggregate(args.shadow_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
