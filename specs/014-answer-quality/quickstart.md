# Quickstart Validation Guide: Answer Quality (spec 014)

**Date**: 2026-07-15

This guide describes how to validate that the answer quality evaluation layer works
end-to-end. It covers the three independently testable validation scenarios that prove
each core user story.

---

## Prerequisites

- Python 3.13 environment with project dependencies installed (`pip install -r requirements.txt`)
- `src/core/answer_quality/` module implemented (see [plan.md](plan.md))
- Golden fixture file present at `tests/fixtures/answer_quality/generic_golden.yaml`
  (see [contracts/interfaces.md](contracts/interfaces.md) for schema)
- Pre-recorded pipeline snapshots (see Snapshot Preparation below)

---

## Snapshot Preparation

The evaluation layer runs offline against **pre-recorded** pipeline outputs. A
snapshot is a `PipelineSnapshot` dataclass:

```python
@dataclass(frozen=True)
class PipelineSnapshot:
    question_id: str          # must match fixture question_id
    answer_result: AnswerResult
    context: Context
    evidence_pack: EvidencePack | None
```

For integration tests, snapshots are created by running the real pipeline against the
golden questions once and serialising the outputs to `tests/fixtures/answer_quality/snapshots/`.
The snapshot loader in `AnswerQualityRegistry.load_snapshots(path)` deserialises them
back into `PipelineSnapshot` objects.

For unit tests, snapshots are constructed inline from minimal Pydantic models (see
test patterns below).

---

## Scenario 1 — Unit: Coverage Evaluator detects a missing source

**Validates**: FR-004, SC-002, User Story 2

```python
# tests/unit/core/answer_quality/test_coverage_evaluator.py

import pytest
from core.answer_quality.coverage.evaluator import DocIdCoverageEvaluator
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.models import GoldenTestFixture, ScoreThresholds
# ... build minimal EvidencePack with one EvidenceItem having doc_id="doc-a"

@pytest.mark.asyncio
async def test_coverage_miss_detected():
    fixture = GoldenTestFixture(
        question_id="q001",
        question="test?",
        expected_source_ids=["doc-a", "doc-b"],   # doc-b is missing
    )
    pack = build_evidence_pack(doc_ids=["doc-a"])  # only doc-a present

    result = await DocIdCoverageEvaluator().evaluate(fixture, pack, default_config())

    assert result.coverage_score == pytest.approx(0.5)
    assert "doc-b" in result.missing_source_ids
    assert result.passed is False
```

**Expected outcome**: `coverage_score=0.5`, `missing_source_ids=["doc-b"]`,
`passed=False`.

---

## Scenario 2 — Unit: Faithfulness scorer flags an unsupported claim

**Validates**: FR-005, SC-003, User Story 3

```python
# tests/unit/core/answer_quality/test_faithfulness_scorer.py

@pytest.mark.asyncio
async def test_fabricated_claim_detected():
    # Context block contains only "325 mg every 4 hours"
    context = build_context(block_texts=["The standard dose is 325 mg every 4 hours."])

    # Answer introduces "500 mg" which is not in any block
    answer_result = build_answer_result(answer="Take 500 mg every 4 hours.")

    fixture = GoldenTestFixture(question_id="q001", question="dose?")
    result = await TextFaithfulnessScorer().score(fixture, answer_result, context, default_config())

    assert result.faithfulness_score is not None
    assert result.faithfulness_score < 1.0
    assert any("500" in claim for claim in result.unsupported_claims)
    assert result.passed is False
```

**Expected outcome**: `faithfulness_score < 1.0`, `"500 mg"` (or similar) in
`unsupported_claims`, `passed=False`.

---

## Scenario 3 — Unit: Completeness scorer detects a partial answer

**Validates**: FR-006, SC-004, User Story 4

```python
# tests/unit/core/answer_quality/test_completeness_scorer.py

@pytest.mark.asyncio
async def test_partial_answer_detected():
    fixture = GoldenTestFixture(
        question_id="q001",
        question="dose and contraindications?",
        expected_answer_facets=["325 mg", "avoid if allergic to aspirin"],
    )
    # Answer covers dosage but not contraindications
    answer_result = build_answer_result(answer="The dose is 325 mg per tablet.")

    result = await KeywordCompletenessScorer().score(fixture, answer_result, default_config())

    assert result.completeness_score == pytest.approx(0.5)
    assert "325 mg" in result.covered_facets
    assert "avoid if allergic to aspirin" in result.uncovered_facets
    assert result.passed is False
```

**Expected outcome**: `completeness_score=0.5`, one covered, one uncovered facet,
`passed=False`.

---

## Scenario 4 — Integration: Full golden suite with known-good snapshot

**Validates**: SC-001, SC-007, User Story 1

```bash
# Run from repo root
pytest tests/integration/test_answer_quality_golden.py -v
```

The integration test:
1. Loads `tests/fixtures/answer_quality/generic_golden.yaml` (≥3 questions).
2. Loads pre-recorded snapshots from `tests/fixtures/answer_quality/snapshots/`.
3. Runs `GoldenTestRunner.run()`.
4. Asserts `EvaluationResult.passed is True` and `aggregate_pass_rate >= 0.9`.
5. Asserts the result is JSON-serialisable (SC-006).

**Expected outcome**: All configured assertions pass; test completes in ≤60 seconds.

---

## Scenario 5 — Integration: Injected degradation causes score drop (SC-002 proof)

**Validates**: SC-002 — "the gate actually detects regressions"

```python
# Inside tests/integration/test_answer_quality_golden.py

@pytest.mark.asyncio
async def test_degraded_snapshot_fails():
    fixtures = load_fixtures("tests/fixtures/answer_quality/generic_golden.yaml")
    snapshots = load_snapshots("tests/fixtures/answer_quality/snapshots/")

    # Degrade: remove all EvidenceItems from the first snapshot's pack
    degraded = degrade_coverage(snapshots, question_id=fixtures[0].question_id)

    runner = AnswerQualityRegistry.default_runner()
    result = await runner.run(fixtures, degraded, default_config())

    # The degraded question must have failed coverage
    q_result = next(r for r in result.question_results if r.question_id == fixtures[0].question_id)
    assert q_result.coverage.passed is False
    assert q_result.coverage.coverage_score is not None
    assert q_result.coverage.coverage_score < 0.7  # SC-002: drop ≥ 0.3 from baseline of 1.0
    assert result.passed is False
```

**Expected outcome**: `coverage_score < 0.7` for the degraded question;
`EvaluationResult.passed=False`; `aggregate_pass_rate < 1.0`.

---

## Scenario 6 — Regression Tracking: score drop identified across two runs

**Validates**: SC-005, User Story 5

```python
# tests/unit/core/answer_quality/test_pipeline.py

@pytest.mark.asyncio
async def test_regression_diff_detects_drop(tmp_path):
    store = JsonRegressionStore(run_store_dir=tmp_path)
    config = default_config()

    result_a = build_evaluation_result(run_id="run-a", coverage_score=1.0)
    result_b = build_evaluation_result(run_id="run-b", coverage_score=0.5)

    await store.save(result_a)
    await store.save(result_b)

    diff = await store.diff("run-a", "run-b", config)

    assert diff.has_regressions is True
    assert any(d.dimension == "coverage" and d.delta < -0.3 for d in diff.regressions)
    assert not diff.improvements  # nothing improved
```

**Expected outcome**: `has_regressions=True`, one `QuestionDelta` with
`dimension="coverage"` and `delta ≤ -0.5`.

---

## Running All Validation Scenarios

```bash
# Unit tests only (fast, no real pipeline required)
pytest tests/unit/core/answer_quality/ -v

# Full integration (requires pre-recorded snapshots)
pytest tests/integration/test_answer_quality_golden.py -v

# Both
pytest tests/unit/core/answer_quality/ tests/integration/test_answer_quality_golden.py -v
```

All tests must pass with exit code 0 for the feature to be considered complete.

---

## References

- Interface contracts → [contracts/interfaces.md](contracts/interfaces.md)
- Output JSON schemas → [contracts/schemas.md](contracts/schemas.md)
- Data model details → [data-model.md](data-model.md)
- Research decisions → [research.md](research.md)
