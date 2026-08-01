#!/usr/bin/env python3
"""Run golden fixtures through the unified orchestrator and emit EvaluationResult JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow running from repo root or src/
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


async def _run(fixtures_path: Path, out_path: Path) -> int:
    from services.rag.pipeline.snapshot_builder import build_pipeline_snapshot

    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    if isinstance(fixtures, dict):
        cases = fixtures.get("cases") or fixtures.get("fixtures") or [fixtures]
    else:
        cases = fixtures

    results = []
    passed = 0
    for case in cases:
        # Offline stub: without a live factory, record structural readiness only.
        question = case.get("question") or case.get("query") or ""
        expected = case.get("expected_answer") or case.get("answer")
        entry = {
            "question": question,
            "expected_answer": expected,
            "status": "skipped_no_runtime",
            "snapshot": None,
        }
        results.append(entry)

    payload = {
        "pass_rate": passed / len(results) if results else 0.0,
        "total": len(results),
        "passed": passed,
        "results": results,
        "note": "Wire build_rag_pipeline_factory + fixtures for full offline golden runs.",
        "snapshot_builder": build_pipeline_snapshot.__name__,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(results)} cases)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=_ROOT / "tests" / "fixtures" / "answer_quality" / "golden.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_ROOT / "eval_run" / "unified_golden_result.json",
    )
    args = parser.parse_args()
    if not args.fixtures.exists():
        # Emit empty result for CI scaffolding when fixtures are absent.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps({"pass_rate": 0.0, "total": 0, "passed": 0, "results": []}, indent=2),
            encoding="utf-8",
        )
        print(f"Fixtures missing at {args.fixtures}; wrote empty result to {args.out}")
        return 0
    return asyncio.run(_run(args.fixtures, args.out))


if __name__ == "__main__":
    raise SystemExit(main())
