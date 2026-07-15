# Tasks: Answer Quality

**Input**: Design documents from `specs/014-answer-quality/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Required per constitution (Principle VII) — included for every user story.

**Implementation note**: US2 (Coverage Evaluator) and US3/US4 (Faithfulness + Completeness
Scorers) are prerequisites for US1 (Golden Test Runner) because the runner orchestrates
all three scorers. Build scorers first, wire the runner second.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on sibling tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory skeleton and seed files that everything else depends on.

- [X] T001 Create module directory structure: `src/core/answer_quality/` with sub-dirs `coverage/`, `faithfulness/`, `completeness/`, `regression/`; `tests/unit/core/answer_quality/`; `tests/fixtures/answer_quality/snapshots/`
- [X] T002 [P] Create `tests/fixtures/answer_quality/generic_golden.yaml` — domain-agnostic golden fixture set with ≥3 questions, `expected_source_ids`, and `expected_answer_facets` per the YAML schema in `contracts/interfaces.md`
- [X] T003 [P] Create `src/fields/generic/answer_quality.yaml` — field-pack config with default thresholds (`coverage: 0.8`, `faithfulness: 0.8`, `completeness: 0.7`), `pass_rate_threshold: 0.9`, `regression_threshold: 0.1`, `completeness_overlap_threshold: 0.5`, `run_store_dir`, `fixture_dir`, `schema_version: "1.0.0"`

---

## Phase 2: Foundational (Core Models, Interfaces, Config, Errors)

**Purpose**: Shared types all user stories depend on — MUST be complete before any story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create `src/core/answer_quality/errors.py` — `EvaluationError`, `FixtureLoadError`, `RunNotFoundError`, `UnmatchedQuestionError`; all inherit from a base `AnswerQualityError`
- [X] T005 [P] Create `src/core/answer_quality/config.py` — `AnswerQualityConfig` (Pydantic, `extra="forbid"`), `load_config_from_yaml(path)`, `resolve_answer_quality_config(domain_key, project_overrides)` following the same pattern as `core.answer_generation.config`
- [X] T006 Create `src/core/answer_quality/models.py` — all domain models: `ScoreThresholds`, `GoldenTestFixture`, `PipelineSnapshot` (dataclass), `CoverageResult`, `FaithfulnessResult`, `CompletenessResult`, `GoldenTestResult`, `EvaluationResult` (`schema_version = "1.0.0"`), `QuestionDelta`, `RegressionDiff`; all Pydantic frozen models per `data-model.md`
- [X] T007 Create `src/core/answer_quality/interfaces.py` — all five ABCs: `IGoldenTestRunner`, `ICoverageEvaluator`, `IFaithfulnessScorer`, `ICompletenessScorer`, `IRegressionStore` with exact signatures from `contracts/interfaces.md`
- [X] T008 [P] Create `src/core/answer_quality/__init__.py` exporting public surface; create empty `__init__.py` files for all sub-packages (`coverage/`, `faithfulness/`, `completeness/`, `regression/`)
- [X] T009 Create `tests/unit/core/answer_quality/conftest.py` — shared pytest fixtures: `default_config()`, `build_evidence_pack(doc_ids)`, `build_context(block_texts)`, `build_answer_result(answer, no_answer=False)`, `build_golden_fixture(question_id, expected_source_ids, expected_answer_facets)` builders used across all unit test files
- [X] T010 Create `tests/unit/core/answer_quality/test_models.py` — validate `GoldenTestFixture` with no optional fields (N/A defaults); `EvaluationResult` serialises to valid JSON; `ScoreThresholds` rejects values outside [0.0, 1.0]; `GoldenTestResult.passed` logic; `RegressionDiff.has_regressions`

**Checkpoint**: Foundation ready — all story phases can now begin.

---

## Phase 3: User Story 2 — Coverage Evaluator (Priority: P1)

**Goal**: Detect whether retrieval surfaced all expected source documents for each golden question.

**Independent Test**: Construct a fixture requiring `[doc-a, doc-b, doc-c]`; pass an `EvidencePack` containing only `[doc-a]`; assert `coverage_score ≈ 0.33`, `missing_source_ids = [doc-b, doc-c]`, `passed = False`.

### Tests for User Story 2 ⚠️

- [X] T011 [P] [US2] Create `tests/unit/core/answer_quality/test_coverage_evaluator.py` — four tests: (1) all required docs present → `score=1.0`, `passed=True`; (2) partial match → `score=0.33`, missing sources listed, `passed=False`; (3) `expected_source_ids=None` → `not_applicable=True`, `passed=True`; (4) `evidence_pack=None` → `not_applicable=True`, `passed=True`

### Implementation for User Story 2

- [X] T012 [US2] Create `src/core/answer_quality/coverage/evaluator.py` — `DocIdCoverageEvaluator(ICoverageEvaluator)`: extract `{item.doc_id for item in evidence_pack.items}`; compute `found = expected ∩ actual`; `coverage_score = len(found)/len(expected)`; populate `missing_source_ids`; apply `fixture.thresholds.coverage ?? config.global_thresholds.coverage`; handle N/A when `expected_source_ids` is absent or `evidence_pack` is `None`; register in `src/core/answer_quality/registry.py`

**Checkpoint**: US2 independently testable — run `pytest tests/unit/core/answer_quality/test_coverage_evaluator.py`.

---

## Phase 4: User Stories 3 & 4 — Faithfulness + Completeness Scorers (Priority: P2)

**Goal**: Detect fabricated claims in answers (US3) and identify multi-part questions answered incompletely (US4). Both scorers are independent and can be implemented in parallel.

**Independent Test US3**: Construct `Context` with blocks containing "325 mg every 4 hours"; construct `AnswerResult` containing "500 mg"; assert `faithfulness_score < 1.0`, `"500"` in `unsupported_claims`, `passed=False`.

**Independent Test US4**: Fixture with `expected_answer_facets=["325 mg", "avoid if allergic"]`; answer contains "325 mg" only; assert `completeness_score ≈ 0.5`, uncovered facets listed, `passed=False`.

### Tests for User Story 3 ⚠️

- [X] T013 [P] [US3] Create `tests/unit/core/answer_quality/test_faithfulness_scorer.py` — five tests: (1) all claims in corpus → `score=1.0`; (2) fabricated number not in blocks → `score<1.0`, span in `unsupported_claims`; (3) `no_answer=True` → `not_applicable=True`; (4) empty `ordered_blocks` → `not_applicable=True`; (5) empty answer string → `not_applicable=True`

### Tests for User Story 4 ⚠️

- [X] T014 [P] [US4] Create `tests/unit/core/answer_quality/test_completeness_scorer.py` — four tests: (1) all facets covered → `score=1.0`; (2) one of two facets missing → `score=0.5`, uncovered facet listed; (3) no `expected_answer_facets` → `not_applicable=True`; (4) `no_answer=True` → `not_applicable=True`

### Implementation for User Story 3

- [X] T015 [US3] Create `src/core/answer_quality/faithfulness/scorer.py` — `TextFaithfulnessScorer(IFaithfulnessScorer)`: (1) guard: return N/A if `answer_result.no_answer` or `context.ordered_blocks` empty; (2) build `source_corpus` = union of `block.text.lower()` across `ordered_blocks`; (3) extract claim spans from `answer_result.answer` using regex for numbers (`\d+[\.,]?\d*\s*\w*`), title-cased bi-grams, and quoted strings; (4) for each span check presence in `source_corpus`; (5) `faithfulness_score = 1 - len(unsupported)/max(len(spans), 1)`; (6) apply threshold; register in `src/core/answer_quality/registry.py`

### Implementation for User Story 4

- [X] T016 [P] [US4] Create `src/core/answer_quality/completeness/scorer.py` — `KeywordCompletenessScorer(ICompletenessScorer)`: (1) guard: return N/A if `no expected_answer_facets` or `answer_result.no_answer`; (2) tokenise each facet and the answer (lowercase, split on non-alpha, strip common stop-words); (3) facet "covered" if `len(facet_tokens ∩ answer_tokens) / len(facet_tokens) >= config.completeness_overlap_threshold`; (4) `completeness_score = covered/total`; (5) apply threshold; register in `src/core/answer_quality/registry.py`

**Checkpoint**: US3 + US4 independently testable — run `pytest tests/unit/core/answer_quality/test_faithfulness_scorer.py tests/unit/core/answer_quality/test_completeness_scorer.py`.

---

## Phase 5: User Story 1 — Golden Test Runner (Priority: P1)

**Goal**: Orchestrate all three scorers over a full fixture set and produce a JSON-serialisable `EvaluationResult` suitable for CI gating.

**Depends on**: Phase 3 (US2) and Phase 4 (US3 + US4) complete.

**Independent Test**: Load `generic_golden.yaml` + pre-recorded snapshots; run `GoldenTestRunner.run()`; assert `EvaluationResult.passed=True`, result JSON-serialisable, run completes in ≤60 s.

### Tests for User Story 1 ⚠️

- [X] T017 [P] [US1] Create unit tests in `tests/unit/core/answer_quality/test_pipeline.py` — five tests: (1) known-good snapshot set → `passed=True`, `aggregate_pass_rate=1.0`; (2) snapshot with missing source → `passed=False`; (3) empty fixtures list → raises `EvaluationError`; (4) unmatched question ID (fixture has question not in snapshots) → raises `UnmatchedQuestionError`; (5) `EvaluationResult` is JSON-serialisable via `model.model_dump_json()`

### Implementation for User Story 1

- [X] T018 [US1] Create `src/core/answer_quality/pipeline.py` — `GoldenTestRunner(IGoldenTestRunner)`: (1) validate `fixtures` non-empty, raise `EvaluationError` if empty; (2) match each fixture to its `PipelineSnapshot` by `question_id`, raise `UnmatchedQuestionError` for any unmatched; (3) for each matched pair call `ICoverageEvaluator.evaluate()`, `IFaithfulnessScorer.score()`, `ICompletenessScorer.score()` concurrently (`asyncio.gather`); (4) assemble `GoldenTestResult` per question (thread `plan_id` from `answer_result.plan_id`); (5) aggregate into `EvaluationResult` (mean scores across applicable questions; `passed = aggregate_pass_rate >= config.pass_rate_threshold`); (6) emit structured log per question (INFO: `run_id`, `question_id`, all dimension scores, `passed`; WARNING on any failed dimension with missing sources / unsupported claims)
- [X] T019 [US1] Complete `src/core/answer_quality/registry.py` — `AnswerQualityRegistry.default_runner()` returns a `GoldenTestRunner` wired with `DocIdCoverageEvaluator`, `TextFaithfulnessScorer`, `KeywordCompletenessScorer`; `AnswerQualityRegistry.load_fixtures(path)` loads and validates YAML against `GoldenTestFixture` (raises `FixtureLoadError` on schema violation)
- [X] T020 [US1] Create snapshot serialisation helpers in `tests/fixtures/answer_quality/` — `save_snapshot(snapshot, path)` / `load_snapshot(path)` functions (JSON via Pydantic `model_dump_json`) and a `degrade_coverage(snapshots, question_id)` helper that returns a copy with an empty `EvidencePack` for the named question
- [X] T021 [US1] Create `tests/integration/test_answer_quality_golden.py` — two integration tests: (1) known-good run: load `generic_golden.yaml` + real snapshots, run runner, assert `passed=True` and JSON round-trip (SC-001, SC-006, SC-007); (2) degraded run: call `degrade_coverage()` on first question's snapshot, re-run, assert `coverage.passed=False` and `coverage_score` drop ≥0.3 (SC-002)

**Checkpoint**: US1 fully functional — run `pytest tests/unit/core/answer_quality/test_pipeline.py tests/integration/test_answer_quality_golden.py`.

---

## Phase 6: User Story 5 — Regression Tracking (Priority: P3)

**Goal**: Persist `EvaluationResult` records per CI run and produce a diff report identifying questions whose scores regressed.

**Independent Test**: Persist two synthetic `EvaluationResult` objects (run-A: coverage=1.0; run-B: coverage=0.5 on same question); call `store.diff("run-a", "run-b")`; assert `has_regressions=True`, delta ≤ -0.5.

### Tests for User Story 5 ⚠️

- [X] T022 [P] [US5] Create `tests/unit/core/answer_quality/test_regression_store.py` — five tests: (1) save + load round-trip (JSON equality); (2) `list_runs()` returns IDs sorted by `run_at` ascending; (3) diff detects coverage drop ≥ threshold → `has_regressions=True`; (4) no-prior-baseline: `diff` raises `RunNotFoundError` for unknown `run_id`; (5) re-save with same `run_id` overwrites without error

### Implementation for User Story 5

- [X] T023 [US5] Create `src/core/answer_quality/regression/store.py` — `JsonRegressionStore(IRegressionStore)`: (1) `save()`: write `{run_id}.json` to `config.run_store_dir` via `EvaluationResult.model_dump_json()`; create dir if absent; idempotent (overwrite on same `run_id`); (2) `load()`: read and validate via `EvaluationResult.model_validate_json()`; raise `RunNotFoundError` if file absent; (3) `list_runs()`: list `*.json` files, parse `run_at` from each, sort ascending, return `run_id` list; (4) `diff()`: load both runs, compare per-question per-dimension scores, emit `QuestionDelta` for changes where `|delta| >= config.regression_threshold`, separate into `regressions` (delta < 0) and `improvements` (delta > 0), set `has_regressions`

**Checkpoint**: US5 independently testable — run `pytest tests/unit/core/answer_quality/test_regression_store.py`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, edge case hardening, and CI readiness.

- [X] T024 [P] Add `no_answer` edge case handling to `src/core/answer_quality/pipeline.py` — when `answer_result.no_answer=True`, runner must record N/A for both faithfulness and completeness (not failure); log a WARNING with `question_id` and `no_answer=True` (FR-011)
- [X] T025 [P] Add exit-code convention to `src/core/answer_quality/registry.py` — `AnswerQualityRegistry.run_and_exit(fixtures, snapshots, config)` synchronous wrapper that calls `asyncio.run(runner.run(...))` and raises `SystemExit(0)` on `passed=True`, `SystemExit(1)` on `passed=False`, `SystemExit(2)` on `EvaluationError` (FR-014, SC-006)
- [X] T026 Run all validation scenarios from `quickstart.md` — execute `pytest tests/unit/core/answer_quality/ tests/integration/test_answer_quality_golden.py -v` and confirm all 6 scenarios (coverage miss, faithfulness flag, completeness partial, known-good run, degraded run, regression diff) pass with exit code 0

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T002 and T003 are parallel
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all story phases; T005, T008, T009 are parallel after T004 is done; T006 must precede T007
- **US2 (Phase 3)**: Depends on Phase 2 — T011 and T012 are sequential (test then implement)
- **US3+US4 (Phase 4)**: Depends on Phase 2 — T013/T014 (tests) parallel; T015/T016 (impls) parallel after their respective tests
- **US1 (Phase 5)**: Depends on Phases 3 + 4 complete — all scorer implementations must exist before the runner can orchestrate them
- **US5 (Phase 6)**: Depends on Phase 5 — regression store needs `EvaluationResult` model (Phase 2) and can be independently exercised; T022 and T023 are sequential
- **Polish (Phase 7)**: Depends on Phases 3–6

### User Story Dependencies

- **US2 (P1)**: Depends on Phase 2 only — no dependency on other user stories
- **US3 (P2)**: Depends on Phase 2 only — independent of US2
- **US4 (P2)**: Depends on Phase 2 only — independent of US2 and US3
- **US1 (P1)**: Depends on US2 + US3 + US4 complete — runner requires all three scorer implementations
- **US5 (P3)**: Depends on Phase 2 models only — independent; can start after Phase 2

### Within Each Phase

- Write tests first (confirm they fail); implement until tests pass
- Models before services; interfaces before implementations
- Register in `registry.py` as each implementation is completed

### Parallel Opportunities

- T002 and T003 (Phase 1) — different files
- T005, T008, T009 (Phase 2) — different files
- T013 and T014 (Phase 4 tests) — different files
- T015 and T016 (Phase 4 impls) — different files
- T024 and T025 (Phase 7) — different files
- US3 and US4 (Phases 4) can be assigned to different developers simultaneously

---

## Parallel Example: Phase 4 (US3 + US4)

```
# Two developers can work simultaneously after Phase 2 completes:

Developer A — User Story 3 (Faithfulness):
  Task: T013 — test_faithfulness_scorer.py
  Task: T015 — faithfulness/scorer.py

Developer B — User Story 4 (Completeness):
  Task: T014 — test_completeness_scorer.py
  Task: T016 — completeness/scorer.py

# Merge both branches before starting Phase 5 (Runner)
```

---

## Implementation Strategy

### MVP: User Story 1 + US2 (Coverage Only)

The minimum demonstrable system: a runner that scores coverage and reports pass/fail.

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Foundational)
3. Complete Phase 3 (US2 — Coverage Evaluator)
4. Complete Phase 5 T018–T019 with stubs for faithfulness and completeness (return N/A)
5. **STOP and VALIDATE**: Run integration test with coverage-only snapshots

### Full v1 Delivery

1. Setup + Foundational
2. US2 Coverage → US3 Faithfulness + US4 Completeness (parallel)
3. US1 Runner (wires all three)
4. US5 Regression Tracking
5. Polish

### Test Count Per Story

| Story | Unit tests | Integration tests |
|-------|-----------|-------------------|
| US2 Coverage | 4 | — |
| US3 Faithfulness | 5 | — |
| US4 Completeness | 4 | — |
| US1 Runner | 5 | 2 |
| US5 Regression | 5 | — |
| Models | 5 | — |
| **Total** | **28** | **2** |

---

## Notes

- `[P]` tasks target different files and have no dependency on sibling tasks in the same phase
- `[Story]` label maps each task to a user story for traceability
- Each story phase is independently completable and testable before the next story begins
- Tests must be written before implementation and confirmed to fail first
- Commit after each phase checkpoint
- `registry.py` is updated incrementally as each implementation is completed (T012 → T015 → T016 → T019)
