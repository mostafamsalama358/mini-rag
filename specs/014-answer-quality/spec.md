# Feature Specification: Answer Quality

**Feature Branch**: `014-answer-quality`

**Created**: 2026-07-15

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Run a Golden Test Suite Against the Full Pipeline (Priority: P1)

A pipeline engineer wants to confirm that a code change to any stage (006–013) has not
degraded answer quality. They run the golden test suite, which executes each golden
question end-to-end and reports per-question scores (coverage, faithfulness,
completeness) and an aggregate pass/fail result.

**Why this priority**: This is the core regression guard. Every pipeline change must
be verified against golden questions before merging. Without it, quality drops are
invisible until user complaints surface.

**Independent Test**: Can be tested by loading a small golden fixture file (≥ 3
questions), running the evaluation runner against pre-recorded pipeline outputs, and
asserting that a known-good output produces scores above threshold while a
deliberately degraded output (e.g. missing a required source) produces a score drop.

**Acceptance Scenarios**:

1. **Given** a set of golden questions with expected sources and expected answers,
   **When** the `IGoldenTestRunner` is invoked with real or pre-recorded pipeline
   outputs, **Then** it returns a `GoldenTestResult` per question containing
   individual dimension scores and an overall pass/fail.

2. **Given** all golden questions pass with a known-good pipeline snapshot,
   **When** a single upstream source is artificially removed from a retrieval result,
   **Then** the coverage score for the affected question drops measurably (at least one
   gate threshold is crossed) and the aggregate report marks that question as failed.

3. **Given** an empty or malformed golden fixture file,
   **When** the runner is invoked, **Then** a descriptive error is returned without
   crashing, and no partial scores are persisted.

---

### User Story 2 — Evaluate Coverage of Expected Sources (Priority: P1)

A QA engineer wants to verify that the retrieval stage surfaced all expected sources
for a golden question before generation ran. The `ICoverageEvaluator` compares the
`EvidencePack` outputs (the actual items retrieved by the Retrieval Engine, spec 011)
against the golden fixture's required sources and produces a coverage ratio.

**Why this priority**: Coverage failure is the earliest detectable quality problem in
the pipeline — it diagnoses retrieval before faithfulness or completeness can even
be measured.

**Independent Test**: Can be tested by constructing a fixture with three required
source IDs and passing an `EvidencePack` that contains only two of them; assert the
coverage ratio is 0.67 and the gate status is FAIL.

**Acceptance Scenarios**:

1. **Given** a golden fixture requiring sources `[A, B, C]` and an `EvidencePack`
   containing items `[A, B, C, D]`, **When** `ICoverageEvaluator.evaluate()` is called,
   **Then** the coverage ratio is 1.0 and gate status is PASS.

2. **Given** a golden fixture requiring sources `[A, B, C]` and an `EvidencePack`
   containing only items `[A, D]`, **When** `ICoverageEvaluator.evaluate()` is called,
   **Then** the coverage ratio is 0.33, missing sources `[B, C]` are listed, and
   gate status is FAIL.

3. **Given** a golden fixture with no required sources specified (optional field
   omitted), **When** `ICoverageEvaluator.evaluate()` is called, **Then** coverage
   is reported as N/A and does not block the overall evaluation.

---

### User Story 3 — Score Faithfulness of an Answer Against Its Citations (Priority: P2)

A pipeline engineer wants to detect hallucinations: statements in `AnswerResult.answer`
that are not traceable to any cited chunk in `Context.citation_map`. The
`IFaithfulnessScorer` checks that numbers, entity names, and specific facts
in the answer appear in the cited source material.

**Why this priority**: Faithfulness failures (fabricated facts) are the most harmful
quality defect for a RAG system. Detecting them at evaluation time — even offline —
prevents them from persisting unnoticed.

**Independent Test**: Can be tested by crafting an `AnswerResult` that contains one
sentence supported by a citation and one sentence with a fabricated drug name not
present in any chunk; assert the faithfulness score is below 1.0 and the unsupported
span is identified.

**Acceptance Scenarios**:

1. **Given** an `AnswerResult` whose every factual claim (number, entity, drug name)
   appears verbatim in at least one cited chunk, **When**
   `IFaithfulnessScorer.score()` is called, **Then** faithfulness score is 1.0 and
   no unsupported spans are reported.

2. **Given** an `AnswerResult` containing a specific number (e.g. "500 mg") that
   does not appear in any cited chunk, **When** `IFaithfulnessScorer.score()` is
   called, **Then** the score is less than 1.0 and the offending span is listed in
   `unsupported_claims`.

3. **Given** an `AnswerResult` with an empty answer body, **When**
   `IFaithfulnessScorer.score()` is called, **Then** score is returned as N/A and
   an empty-answer flag is set, without raising an exception.

---

### User Story 4 — Score Completeness of a Multi-Part Answer (Priority: P2)

A pipeline engineer wants to know whether an answer addressed all sub-questions in a
multi-part golden question. The `ICompletenessScorer` checks each expected answer
component against `AnswerResult.answer` and assigns a completeness ratio.

**Why this priority**: Multi-part queries are common in domain RAG (e.g. "What is the
dosage, contraindications, and shelf life?"). Partial answers silently fail users.

**Independent Test**: Can be tested by constructing a three-part golden question with
expected answer facets `[dosage, contraindications, shelf-life]` and an answer that
addresses only `[dosage, contraindications]`; assert completeness score is 0.67.

**Acceptance Scenarios**:

1. **Given** a golden question with two expected answer facets and an answer that
   addresses both, **When** `ICompletenessScorer.score()` is called, **Then**
   completeness score is 1.0 and all facets are marked as covered.

2. **Given** a golden question with three expected answer facets and an answer that
   addresses only one, **When** `ICompletenessScorer.score()` is called, **Then**
   completeness score is 0.33 and the two uncovered facets are listed.

3. **Given** a golden question with no expected answer facets (single-part question),
   **When** `ICompletenessScorer.score()` is called, **Then** completeness is
   reported as N/A rather than a ratio.

---

### User Story 5 — Track Regression Trends Across Commits (Priority: P3)

A team lead wants to see whether the pipeline's quality is trending up or down over
recent commits. The regression tracker persists `GoldenTestResult` sets keyed by a
run identifier (commit hash or timestamp) and exposes a diff summary showing
score changes per question relative to the prior run.

**Why this priority**: Individual run scores are not enough — teams need to know if
a recent change silently moved any score. Trend data surfaces creeping regressions.

**Independent Test**: Can be tested by persisting two synthetic result sets (run A and
run B where one question's coverage score drops from 1.0 to 0.5) and asserting the
diff report flags that question as regressed.

**Acceptance Scenarios**:

1. **Given** two persisted evaluation runs for the same golden set, **When** a
   regression diff is requested, **Then** the report lists questions whose aggregate
   score changed by more than a configurable threshold, with old/new values.

2. **Given** only one persisted run (no prior baseline), **When** a regression diff
   is requested, **Then** the report notes no prior baseline and returns the current
   run as the baseline for future comparisons.

---

### Edge Cases

- What happens when a golden fixture references a source ID that no longer exists in
  the index? The evaluator must log a warning and treat the missing source as
  not-covered rather than raising an exception.
- What happens when `Context.citation_map` is empty (generation ran without retrieval)?
  Faithfulness scorer must return N/A rather than a false 0.0.
- What happens when the pipeline produces an `AnswerResult` with `no_answer = true`?
  Faithfulness and completeness scorers must skip scoring and record a no-answer
  sentinel, not a failure.
- What happens when a golden fixture's expected answer is a regex or fuzzy match?
  The spec assumes exact-text and semantic matching modes; fixtures declare which mode
  applies per question.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The evaluation layer MUST accept `AnswerResult` (spec 013), `Context`
  (spec 012), and `EvidencePack` (spec 011) as read-only inputs; it MUST NOT mutate
  any pipeline object.

- **FR-002**: The system MUST provide a `GoldenTestFixture` schema defining: question
  text, expected source IDs, expected answer facets, match mode (exact / semantic),
  and per-dimension score thresholds.

- **FR-003**: The system MUST provide an `IGoldenTestRunner` interface that accepts a
  fixture set and pipeline outputs and returns a `GoldenTestResult` per question plus
  an `EvaluationResult` aggregate report.

- **FR-004**: The system MUST provide an `ICoverageEvaluator` interface that computes
  the ratio of required sources present in `EvidencePack` outputs and flags which
  required sources are absent.

- **FR-005**: The system MUST provide an `IFaithfulnessScorer` interface that verifies
  factual claims (numbers, entity names, specific terms) in `AnswerResult.answer`
  against cited chunks in `Context.citation_map`, identifies unsupported spans, and
  returns a score in [0.0, 1.0].

- **FR-006**: The system MUST provide an `ICompletenessScorer` interface that checks
  whether each expected answer facet defined in the golden fixture is addressed in
  `AnswerResult.answer` and returns a completeness ratio in [0.0, 1.0].

- **FR-007**: The system MUST support a regression tracking mechanism that persists
  `EvaluationResult` records keyed by run identifier (commit hash or timestamp) and
  can produce a diff report comparing two runs.

- **FR-008**: The `EvaluationResult` schema MUST include: run identifier, timestamp,
  per-question `GoldenTestResult` list, aggregate pass rate, and per-dimension
  aggregate scores (coverage, faithfulness, completeness).

- **FR-009**: The `GoldenTestResult` schema MUST include: question ID, question text,
  coverage score, faithfulness score, completeness score, overall pass/fail verdict,
  and lists of missing sources and unsupported claims.

- **FR-010**: Score thresholds MUST be configurable per fixture and globally via
  configuration; no thresholds MUST be hard-coded.

- **FR-011**: The evaluation layer MUST handle pipeline outputs where
  `AnswerResult.no_answer` is `true` by recording N/A for faithfulness and
  completeness without treating them as failures.

- **FR-012**: The evaluation layer MUST handle missing or absent `Context.citation_map`
  entries gracefully; faithfulness scorer MUST return N/A (not 0.0) when citations are
  absent.

- **FR-013**: Golden test fixture files MUST be loadable from a configurable directory
  path; domain-specific content MUST be injected via fixture files only — no
  domain logic MUST be embedded in evaluation interfaces.

- **FR-014**: The system MUST produce structured output (JSON-serialisable
  `EvaluationResult`) suitable for CI consumption (exit code non-zero on aggregate
  fail) and for human-readable reporting.

- **FR-015**: The evaluation layer MUST run offline/async against pipeline outputs; it
  MUST NOT be invoked in the user-facing request path.

### Key Entities

- **`GoldenTestFixture`**: Represents a single test case. Key attributes: `question_id`
  (str), `question` (str), `expected_source_ids` (list[str], optional),
  `expected_answer_facets` (list[str], optional),
  `thresholds` (CoverageThreshold, FaithfulnessThreshold, CompletenessThreshold).

- **`GoldenTestResult`**: Per-question evaluation output. Key attributes:
  `question_id`, `plan_id` (str, threaded from `Context.plan_id` for run correlation),
  `coverage_score` (float | None), `faithfulness_score` (float | None),
  `completeness_score` (float | None), `missing_sources` (list[str]),
  `unsupported_claims` (list[str]), `passed` (bool).

- **`EvaluationResult`**: Aggregate run output. Key attributes: `run_id` (str),
  `run_at` (datetime), `question_results` (list[GoldenTestResult]),
  `aggregate_pass_rate` (float), `aggregate_coverage` (float | None),
  `aggregate_faithfulness` (float | None), `aggregate_completeness` (float | None),
  `passed` (bool).

- **`IGoldenTestRunner`**: Interface. Methods: `run(fixtures, pipeline_outputs) →
  EvaluationResult`.

- **`ICoverageEvaluator`**: Interface. Methods: `evaluate(fixture, evidence_pack) →
  CoverageResult`.

- **`IFaithfulnessScorer`**: Interface. Methods: `score(fixture, answer_result, context) →
  FaithfulnessResult`.

- **`ICompletenessScorer`**: Interface. Methods: `score(fixture, answer_result) →
  CompletenessResult`.

- **`IRegressionStore`**: Interface. Methods: `save(result) → Path`,
  `load(run_id) → EvaluationResult`, `list_runs() → list[str]`,
  `diff(run_id_baseline, run_id_current) → RegressionDiff`. Persists
  `EvaluationResult` records for regression tracking; v1 concrete implementation is
  `JsonRegressionStore` (JSON files in a configurable directory).

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: The evaluation layer MUST respect Clean Architecture boundaries —
  evaluation logic lives in an application/service layer; persistence of results lives
  in infrastructure; interfaces are defined independent of any concrete scorer.

- **NFR-002**: All evaluation I/O paths MUST be async; public scorer methods MUST
  include type hints and Pydantic-backed output models.

- **NFR-003**: Concrete scorer implementations MUST be registered via a factory or
  dependency injection mechanism; callers depend on `IFaithfulnessScorer`, not on a
  specific implementation.

- **NFR-004**: `EvaluationResult` MUST be JSON-serialisable and include `run_id` for
  correlation with upstream pipeline runs; the `plan_id` from `Context.plan_id` MUST
  be threaded into `GoldenTestResult` for traceability.

- **NFR-005**: Unit tests MUST cover all scorer interfaces with at least one pass and
  one fail scenario per dimension; integration tests MUST run the full golden suite
  against a recorded pipeline snapshot.

- **NFR-006**: Evaluation runs MUST emit structured logs including `run_id`,
  `question_id`, per-dimension scores, and `passed` status at INFO level; failures
  MUST include the missing source IDs or unsupported claim spans.

- **NFR-007**: No pharmacy-specific or domain-specific logic MUST appear in any
  interface implementation; all domain content enters exclusively through fixture files.

- **NFR-008**: The golden test runner MUST return a non-zero exit code (or raise a
  structured exception) when aggregate pass rate falls below the configured threshold,
  enabling CI integration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given the golden query set (minimum 10 questions), the evaluation layer
  produces a complete `EvaluationResult` with per-question coverage, faithfulness, and
  completeness scores and an aggregate report within 60 seconds of invocation on
  pre-recorded pipeline outputs.

- **SC-002**: A deliberately degraded pipeline component — specifically, a retrieval
  result with at least one required source artificially removed — causes a measurable
  score drop on the affected question's coverage score (drop ≥ 0.3 from baseline) and
  the aggregate report marks that question as failed, proving the gate detects
  regressions rather than passing everything.

- **SC-003**: A `GoldenTestResult` containing a fabricated entity name (not present in
  any cited chunk) achieves a faithfulness score ≤ 0.8, demonstrating that the
  faithfulness scorer catches unsupported claims rather than accepting any answer.

- **SC-004**: An answer that addresses only half of a two-part golden question achieves
  a completeness score ≤ 0.6, demonstrating sensitivity to partial answers.

- **SC-005**: Regression tracking correctly identifies a score drop between two
  consecutive evaluation runs — when one question's coverage score moves from 1.0 to
  0.5, the diff report flags it as regressed and does not report any false regressions
  on stable questions.

- **SC-006**: The evaluation layer's output is machine-consumable: `EvaluationResult`
  serialises to valid JSON, and a CLI or test harness exit code is non-zero when
  aggregate pass rate falls below the configured threshold.

- **SC-007**: The golden fixture format is domain-agnostic: the same runner, evaluator,
  and scorer implementations work without modification when fixture files are replaced
  with a completely different domain's questions and sources.

## Assumptions

- Golden test fixtures are maintained by the team as versioned files in the repository;
  no UI for fixture authoring is in scope for this feature.
- The evaluation layer will be invoked by CI (on PR merge) and by engineers manually;
  real-time user-facing invocation is explicitly out of scope.
- `Context.citation_map` keys use `item_id` values (`ei_` prefix), consistent with
  spec 012; the faithfulness scorer uses these keys as the authoritative lookup
  for cited chunks.
- `EvidencePack` from spec 011 is the authoritative source for coverage evaluation
  because it records all items actually retrieved by the Retrieval Engine before
  context budget trimming; using `Context.citation_map` alone would under-count
  coverage for sources that were retrieved but dropped due to token budget limits.
  If `EvidencePack` is not available (e.g. a replay scenario uses only `AnswerResult`
  + `Context`), coverage evaluation is skipped and marked N/A.
- The faithfulness scorer uses text-matching heuristics (exact substring and
  named-entity matching) for v1; a semantic embedding-based scorer is a valid future
  implementation of the same `IFaithfulnessScorer` interface.
- Regression tracking persistence uses local file storage (JSON) for v1; a database-backed
  store is a valid future implementation of the same persistence interface.
- `IGroundingChecker` (spec 013) remains the lightweight inline guard in the
  user-facing answer path; `IFaithfulnessScorer` is the deeper offline scorer and the
  two are complementary, not duplicated.
- Score thresholds default to 0.8 for coverage, 0.8 for faithfulness, and 0.7 for
  completeness unless overridden per fixture or globally in configuration.
- The evaluation layer consumes pipeline outputs as data objects (Pydantic models);
  it does not call any live LLM or external API in its core scoring logic (LLM-based
  scoring is an optional future extension behind the interface).
