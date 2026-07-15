# Data Model: Answer Quality (spec 014)

**Date**: 2026-07-15 | **Source**: research.md + spec.md Key Entities

All models are frozen Pydantic `BaseModel` instances, consistent with the project
convention established in `context_builder/models.py` and
`answer_generation/models.py`.

---

## Input Models (consumed read-only, defined upstream)

These types are imported; this spec does not redefine them.

| Type | Source module | Key fields used by answer_quality |
|------|--------------|----------------------------------|
| `AnswerResult` | `core.answer_generation.models` | `answer`, `citations`, `no_answer`, `plan_id`, `context_id` |
| `Context` | `core.context_builder.models` | `ordered_blocks[*].text`, `citation_map`, `plan_id`, `context_id` |
| `EvidencePack` | `core.evidence_orchestrator.models` | `items[*].doc_id`, `items[*].text`, `plan_id` |
| `EvidenceItem` | `core.evidence_orchestrator.models` | `doc_id`, `chunk_id`, `item_id`, `text` |
| `ContextBlock` | `core.context_builder.models` | `item_id`, `text`, `document_id` |

---

## Domain Models (defined by this spec)

### `ScoreThresholds`

Per-dimension pass/fail thresholds. Used both globally (in `AnswerQualityConfig`) and
per fixture (in `GoldenTestFixture`).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `coverage` | `float \| None` | `0.8` | Minimum coverage ratio to pass |
| `faithfulness` | `float \| None` | `0.8` | Minimum faithfulness score to pass |
| `completeness` | `float \| None` | `0.7` | Minimum completeness score to pass |

Validation: each field, when not `None`, must be in `[0.0, 1.0]`.

---

### `GoldenTestFixture`

A single test case in the golden set. Loaded from YAML fixture files.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question_id` | `str` | ✅ | Stable unique identifier, e.g. `"q001"` |
| `question` | `str` | ✅ | The natural-language question text |
| `expected_source_ids` | `list[str] \| None` | optional | Document IDs expected in `EvidencePack.items[*].doc_id`; omit to skip coverage scoring |
| `expected_answer_facets` | `list[str] \| None` | optional | Answer components that must be addressed; omit to skip completeness scoring |
| `thresholds` | `ScoreThresholds \| None` | optional | Per-question threshold overrides; merges with global config |

---

### `CoverageResult`

Output of `ICoverageEvaluator.evaluate()`.

| Field | Type | Description |
|-------|------|-------------|
| `question_id` | `str` | Matches `GoldenTestFixture.question_id` |
| `coverage_score` | `float \| None` | `covered / required`; `None` when `expected_source_ids` is absent |
| `missing_source_ids` | `list[str]` | IDs in `expected_source_ids` not found in `EvidencePack` |
| `found_source_ids` | `list[str]` | IDs that were found |
| `not_applicable` | `bool` | `True` when fixture has no `expected_source_ids` |
| `passed` | `bool` | `coverage_score >= threshold`; `True` when `not_applicable` |

---

### `FaithfulnessResult`

Output of `IFaithfulnessScorer.score()`.

| Field | Type | Description |
|-------|------|-------------|
| `question_id` | `str` | Matches `GoldenTestFixture.question_id` |
| `faithfulness_score` | `float \| None` | `1 - unsupported/total_spans`; `None` when not applicable |
| `unsupported_claims` | `list[str]` | Claim spans not traceable to `Context.ordered_blocks[*].text` |
| `total_spans_checked` | `int` | Number of candidate claim spans extracted from the answer |
| `not_applicable` | `bool` | `True` when `AnswerResult.no_answer=True` or `ordered_blocks` is empty |
| `passed` | `bool` | `faithfulness_score >= threshold`; `True` when `not_applicable` |

---

### `CompletenessResult`

Output of `ICompletenessScorer.score()`.

| Field | Type | Description |
|-------|------|-------------|
| `question_id` | `str` | Matches `GoldenTestFixture.question_id` |
| `completeness_score` | `float \| None` | `covered_facets / total_facets`; `None` when not applicable |
| `covered_facets` | `list[str]` | Facets judged as addressed in the answer |
| `uncovered_facets` | `list[str]` | Facets not addressed |
| `not_applicable` | `bool` | `True` when `expected_answer_facets` is absent or empty, or `no_answer=True` |
| `passed` | `bool` | `completeness_score >= threshold`; `True` when `not_applicable` |

---

### `GoldenTestResult`

Per-question aggregate of all dimension results. Produced by `IGoldenTestRunner`.

| Field | Type | Description |
|-------|------|-------------|
| `question_id` | `str` | Stable question identifier |
| `question` | `str` | Question text (for human-readable reports) |
| `plan_id` | `str` | Threaded from `Context.plan_id` via `AnswerResult.plan_id` for pipeline correlation |
| `coverage` | `CoverageResult` | Coverage dimension result |
| `faithfulness` | `FaithfulnessResult` | Faithfulness dimension result |
| `completeness` | `CompletenessResult` | Completeness dimension result |
| `passed` | `bool` | `True` iff all applicable dimensions pass |
| `evaluated_at` | `str` | ISO 8601 UTC timestamp |

---

### `EvaluationResult`

Aggregate output of a full golden test run. JSON-serialisable; used for CI gating
and regression tracking.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Stable run identifier; format: `{commit_sha}` or `{YYYYMMDD-HHMMSS}` |
| `run_at` | `str` | ISO 8601 UTC timestamp |
| `question_results` | `list[GoldenTestResult]` | One entry per fixture question |
| `aggregate_pass_rate` | `float` | `passed_questions / total_questions` |
| `aggregate_coverage` | `float \| None` | Mean coverage score across applicable questions |
| `aggregate_faithfulness` | `float \| None` | Mean faithfulness score across applicable questions |
| `aggregate_completeness` | `float \| None` | Mean completeness score across applicable questions |
| `passed` | `bool` | `True` when `aggregate_pass_rate >= config.pass_rate_threshold` |
| `fixture_file` | `str` | Path to the YAML fixture file used |
| `schema_version` | `str` | `"1.0.0"` |

---

### `RegressionDiff`

Output of `IRegressionStore.diff(run_id_a, run_id_b)`.

| Field | Type | Description |
|-------|------|-------------|
| `run_id_baseline` | `str` | Earlier run ID (baseline) |
| `run_id_current` | `str` | Later run ID (current) |
| `regressions` | `list[QuestionDelta]` | Questions where a score dropped by more than `regression_threshold` |
| `improvements` | `list[QuestionDelta]` | Questions where a score improved |
| `stable` | `list[str]` | Question IDs with no significant change |
| `has_regressions` | `bool` | `True` if `regressions` is non-empty |

### `QuestionDelta`

One question's score movement between two runs.

| Field | Type | Description |
|-------|------|-------------|
| `question_id` | `str` | — |
| `dimension` | `Literal["coverage", "faithfulness", "completeness", "overall"]` | Which dimension changed |
| `baseline_score` | `float \| None` | Score in the baseline run |
| `current_score` | `float \| None` | Score in the current run |
| `delta` | `float \| None` | `current - baseline`; negative = regression |

---

## Configuration Model

### `AnswerQualityConfig`

Loaded from `src/fields/generic/answer_quality.yaml`; domain packs may override.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `global_thresholds` | `ScoreThresholds` | `{coverage: 0.8, faithfulness: 0.8, completeness: 0.7}` | Global pass/fail thresholds |
| `pass_rate_threshold` | `float` | `0.9` | Minimum fraction of questions that must pass for aggregate `EvaluationResult.passed=True` |
| `regression_threshold` | `float` | `0.1` | Minimum score drop to classify a question as regressed |
| `completeness_overlap_threshold` | `float` | `0.5` | Minimum token-set overlap fraction for a facet to be "covered" |
| `run_store_dir` | `str` | `".answer_quality/runs"` | Directory for persisting `EvaluationResult` JSON files |
| `fixture_dir` | `str` | `"tests/fixtures/answer_quality"` | Default directory scanned for `*.yaml` fixture files |
| `schema_version` | `str` | `"1.0.0"` | Config schema version |

---

## State Transitions

```
GoldenTestFixture (YAML) ──load──► GoldenTestRunner.run()
                                        │
              ┌─────────────────────────┼───────────────────────────┐
              ▼                         ▼                           ▼
   ICoverageEvaluator            IFaithfulnessScorer       ICompletenessScorer
   .evaluate(fixture,            .score(answer_result,     .score(answer_result,
             evidence_pack)               context)                  fixture)
              │                         │                           │
              ▼                         ▼                           ▼
      CoverageResult           FaithfulnessResult          CompletenessResult
              └─────────────────────────┼───────────────────────────┘
                                        ▼
                               GoldenTestResult (per question)
                                        │
                              aggregate across fixture set
                                        ▼
                               EvaluationResult
                                        │
                              IRegressionStore.save()
                                        │
                              (optional) .diff() ──► RegressionDiff
```
