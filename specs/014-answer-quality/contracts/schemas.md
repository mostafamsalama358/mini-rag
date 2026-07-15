# Output Schemas: Answer Quality (spec 014)

**Date**: 2026-07-15

These are the wire-format schemas for `EvaluationResult` and `RegressionDiff` — the
two primary outputs consumed by CI and by the regression tracker.

---

## `EvaluationResult` JSON Schema (v1.0.0)

Produced by `IGoldenTestRunner.run()` and persisted by `IRegressionStore.save()`.

```json
{
  "schema_version": "1.0.0",
  "run_id": "a1b2c3d4",
  "run_at": "2026-07-15T09:12:00Z",
  "fixture_file": "tests/fixtures/answer_quality/generic_golden.yaml",
  "passed": true,
  "aggregate_pass_rate": 1.0,
  "aggregate_coverage": 0.95,
  "aggregate_faithfulness": 0.88,
  "aggregate_completeness": 0.91,
  "question_results": [
    {
      "question_id": "q001",
      "question": "What is the adult dose of aspirin?",
      "plan_id": "plan_4a7b3c9d1e2f5678",
      "evaluated_at": "2026-07-15T09:12:01Z",
      "passed": true,
      "coverage": {
        "question_id": "q001",
        "coverage_score": 1.0,
        "missing_source_ids": [],
        "found_source_ids": ["doc-aspirin-pil"],
        "not_applicable": false,
        "passed": true
      },
      "faithfulness": {
        "question_id": "q001",
        "faithfulness_score": 1.0,
        "unsupported_claims": [],
        "total_spans_checked": 4,
        "not_applicable": false,
        "passed": true
      },
      "completeness": {
        "question_id": "q001",
        "completeness_score": 1.0,
        "covered_facets": ["325 mg", "every 4 to 6 hours"],
        "uncovered_facets": [],
        "not_applicable": false,
        "passed": true
      }
    }
  ]
}
```

### Failure example (coverage miss)

```json
{
  "schema_version": "1.0.0",
  "run_id": "b2c3d4e5",
  "run_at": "2026-07-15T10:00:00Z",
  "fixture_file": "tests/fixtures/answer_quality/generic_golden.yaml",
  "passed": false,
  "aggregate_pass_rate": 0.5,
  "aggregate_coverage": 0.5,
  "aggregate_faithfulness": 0.9,
  "aggregate_completeness": null,
  "question_results": [
    {
      "question_id": "q001",
      "question": "What is the adult dose of aspirin?",
      "plan_id": "plan_deadbeef",
      "evaluated_at": "2026-07-15T10:00:01Z",
      "passed": false,
      "coverage": {
        "question_id": "q001",
        "coverage_score": 0.5,
        "missing_source_ids": ["doc-aspirin-pil"],
        "found_source_ids": [],
        "not_applicable": false,
        "passed": false
      },
      "faithfulness": {
        "question_id": "q001",
        "faithfulness_score": 0.75,
        "unsupported_claims": ["500 mg"],
        "total_spans_checked": 4,
        "not_applicable": false,
        "passed": false
      },
      "completeness": {
        "question_id": "q001",
        "completeness_score": null,
        "covered_facets": [],
        "uncovered_facets": [],
        "not_applicable": true,
        "passed": true
      }
    }
  ]
}
```

---

## `RegressionDiff` JSON Schema

Produced by `IRegressionStore.diff(run_id_baseline, run_id_current)`.

```json
{
  "run_id_baseline": "a1b2c3d4",
  "run_id_current":  "b2c3d4e5",
  "has_regressions": true,
  "regressions": [
    {
      "question_id": "q001",
      "dimension": "coverage",
      "baseline_score": 1.0,
      "current_score": 0.5,
      "delta": -0.5
    }
  ],
  "improvements": [],
  "stable": []
}
```

---

## CI Exit Code Convention

The `GoldenTestRunner` (and its CLI wrapper) MUST exit with:

| Condition | Exit code |
|-----------|-----------|
| `EvaluationResult.passed == True` | `0` |
| `EvaluationResult.passed == False` | `1` |
| Fatal error (fixture load failure, unmatched question IDs) | `2` |

This allows CI pipelines to gate merges on `exit_code != 0`.
