# Tasks: Unified Production Pipeline Migration

**Input**: Design documents from `/specs/015-unified-pipeline-migration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per constitution (Principle VII) — contract and integration tests included for each user story.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5)

## Path Conventions

- Source: `src/`
- Tests: `tests/contract/`, `tests/integration/`, `tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create migration module layout and pipeline configuration surface.

- [X] T001 Create `src/services/rag/pipeline/` package with `__init__.py` exporting `PIPELINE_VERSION = "1.0.0"`
- [X] T002 [P] Create `src/services/rag/adapters/` package with `__init__.py`
- [X] T003 [P] Add pipeline settings to `src/helpers/config.py`: `RAG_PIPELINE_MODE`, `RAG_PIPELINE_FALLBACK_ON_ERROR`, `RAG_PIPELINE_SHADOW_PERSIST`, `RAG_PIPELINE_SHADOW_DIR`, `RAG_PIPELINE_UNIFIED_TIMEOUT_S`, `RAG_PIPELINE_CANARY_PROJECT_IDS`, `RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD`
- [X] T004 [P] Document new env vars in `.env.example` with defaults matching `data-model.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared orchestration types, parsing, adaptation, and telemetry used by all user stories.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T005 [P] Implement orchestration models (`PipelineMode`, `PipelineOutcome`, `StageStatus`, `PipelineStageTrace`, `PipelineSettingsSnapshot`, `PipelineExecutionContext`, `UnifiedPipelineResult`, `PipelineAnswerResponse`, `ShadowComparisonRecord`) in `src/services/rag/pipeline/models.py` per `data-model.md`
- [X] T006 [P] Implement immutable context builder (`build_execution_context`) in `src/services/rag/pipeline/context.py` including `locale`, `deadline_at`, `pipeline_version`, `settings_snapshot`
- [X] T007 [P] Implement `PipelineModeResolver` in `src/services/rag/pipeline/mode_resolver.py` per `contracts/orchestrator.md` resolution order
- [X] T008 [P] Extract `QueryParseService` from `src/services/rag/answer_service.py` into `src/services/rag/pipeline/query_parse_service.py` (single parse path for legacy and unified)
- [X] T009 [P] Implement `type_mapping.py` in `src/services/rag/adapters/type_mapping.py` (`RetrievedDocument` ↔ `RawCandidate`, evidence conversions) per `contracts/adapters.md`
- [X] T010 [P] Implement `ResponseAdapter` in `src/services/rag/pipeline/response_adapter.py` per `contracts/orchestrator.md` signal mapping
- [X] T011 [P] Add pipeline metrics to `src/utils/metrics.py`: `rag_pipeline_requests_total`, `rag_pipeline_stage_duration_seconds`, `rag_shadow_divergence_total`, `pipeline_fallback_total`
- [X] T012 Implement structured pipeline logging in `src/services/rag/pipeline/telemetry.py` (`log_pipeline_complete`, stage trace append helpers)
- [X] T013 [P] Unit tests for mode resolver in `tests/unit/services/rag/pipeline/test_mode_resolver.py`
- [X] T014 [P] Unit tests for context builder and models in `tests/unit/services/rag/pipeline/test_context.py`
- [X] T015 [P] Unit tests for type mapping round-trips in `tests/unit/services/rag/adapters/test_type_mapping.py`

**Checkpoint**: Foundation ready — router and executors can be built.

---

## Phase 3: User Story 1 — Seamless API for Existing Clients (Priority: P1) 🎯 MVP

**Goal**: `/answer` continues to work unchanged via `PipelineRouter` defaulting to legacy execution.

**Independent Test**: `RAG_PIPELINE_MODE=legacy` — same request/response schema and behavior as pre-migration baseline (`quickstart.md` §1).

### Tests for User Story 1

- [X] T016 [P] [US1] Create contract tests asserting frozen JSON schema in `tests/contract/test_answer_api.py` per `contracts/api-stability.md`
- [X] T017 [P] [US1] Create integration test for legacy path parity in `tests/integration/test_pipeline_legacy.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement `LegacyPipelineExecutor` wrapping `RAGService.answer_question` in `src/services/rag/pipeline/legacy_executor.py`
- [X] T019 [US1] Implement `PipelineRouter` with legacy-mode delegation in `src/services/rag/pipeline/router.py`
- [X] T020 [US1] Refactor `NLPController.answer_rag_question` in `src/services/rag/rag_service.py` to delegate to injected `PipelineRouter` (fallback to inline `RAGService` when factory absent)
- [X] T021 [US1] Wire optional `PipelineRouter` construction in `src/routes/nlp.py` for `answer_rag` (legacy-only path without full factory)
- [X] T022 [US1] Emit `rag_pipeline_requests_total{mode="legacy"}` and completion logs from `router.py`

**Checkpoint**: MVP — production-safe with `RAG_PIPELINE_MODE=legacy` (default).

---

## Phase 4: User Story 3 — Instant Rollback (Priority: P1)

**Goal**: Operators flip `RAG_PIPELINE_MODE` (or per-project override) to revert traffic without redeploy.

**Independent Test**: Flag flip from `unified` to `legacy` — next 100 requests execute legacy only (`quickstart.md` §4).

### Tests for User Story 3

- [X] T023 [P] [US3] Integration test for mode resolution and rollback in `tests/integration/test_pipeline_rollback.py`

### Implementation for User Story 3

- [X] T024 [US3] Add per-project `config_json.pipeline_mode` override handling in `src/services/rag/pipeline/mode_resolver.py`
- [X] T025 [US3] Add `RAG_PIPELINE_CANARY_PROJECT_IDS` forced-unified logic in `src/services/rag/pipeline/mode_resolver.py`
- [X] T026 [US3] Log resolved mode on every request in `src/services/rag/pipeline/router.py` for rollback verification

**Checkpoint**: Rollback drillable via config + metric inspection.

---

## Phase 5: User Story 4 — Unified Pipeline Delivers Spec-Quality Answers (Priority: P2)

**Goal**: Unified path runs Parse → Plan → Engine → Evidence → Context → Answer via adapters.

**Independent Test**: `RAG_PIPELINE_MODE=unified` — stage traces show all six stages; API contract still passes (`quickstart.md` §2).

### Tests for User Story 4

- [X] T027 [P] [US4] Integration test for unified stage wiring in `tests/integration/test_unified_pipeline.py`
- [X] T028 [P] [US4] Unit tests for adapter capability validation in `tests/unit/services/rag/adapters/test_capabilities.py`
- [X] T029 [P] [US4] Unit tests for cancellation/timeout policy in `tests/unit/services/rag/pipeline/test_cancellation.py`

### Implementation for User Story 4 — Adapters

- [X] T030 [P] [US4] Implement `AdapterCapabilities` dataclass in `src/services/rag/adapters/capabilities.py`
- [X] T031 [P] [US4] Implement `PgVectorDenseRetriever` in `src/services/rag/adapters/vector_retriever.py`
- [X] T032 [P] [US4] Implement `PgVectorSparseRetriever` in `src/services/rag/adapters/sparse_retriever.py`
- [X] T033 [P] [US4] Implement `StructuredInteractionRetriever` in `src/services/rag/adapters/interaction_retriever.py`
- [X] T034 [P] [US4] Implement `LegacyRerankerAdapter` in `src/services/rag/adapters/reranker_adapter.py`
- [X] T035 [P] [US4] Implement `SqlChunkReader` in `src/services/rag/adapters/chunk_reader.py`
- [X] T036 [P] [US4] Implement `EmbeddingProviderAdapter` in `src/services/rag/adapters/embedding_provider.py`
- [X] T037 [US4] Implement `FieldContextAdapter` (planner/engine/evidence/context/answer config builders) in `src/services/rag/adapters/field_context.py`

### Implementation for User Story 4 — Orchestrator & DI

- [X] T038 [US4] Implement `UnifiedRagOrchestrator` with stage graph and failure-propagation table in `src/services/rag/pipeline/unified_orchestrator.py` per `data-model.md`
- [X] T039 [US4] Implement deadline enforcement and semantic-vs-error fallback rules in `src/services/rag/pipeline/unified_orchestrator.py`
- [X] T040 [US4] Implement `asyncio.CancelledError` re-raise (no fallback) in `src/services/rag/pipeline/router.py` and `unified_orchestrator.py`
- [X] T041 [US4] Implement optional transient retry (max 2) inside vector adapters in `src/services/rag/adapters/vector_retriever.py`
- [X] T042 [US4] Implement `build_rag_pipeline_factory(app)` in `src/services/rag/composition.py` wiring registries, adapters, and startup capability validation per `contracts/adapters.md`
- [X] T043 [US4] Attach `app.rag_pipeline_factory` in `src/main.py` `startup_span()` with fail-fast when mode is `shadow`/`unified` and capabilities missing
- [X] T044 [US4] Extend `PipelineRouter` unified branch with fallback-on-error in `src/services/rag/pipeline/router.py`
- [X] T045 [US4] Wire `answer_rag` route to use `request.app.rag_pipeline_factory` in `src/routes/nlp.py`
- [X] T046 [US4] Rename legacy dataclass `RetrievalResult` to `LegacyRetrievalOutcome` in `src/services/rag/answer_service.py` to avoid engine type collision

**Checkpoint**: Unified mode callable in dev/staging with API contract preserved.

---

## Phase 6: User Story 2 — Safe Rollout with Shadow Mode (Priority: P1)

**Goal**: Dual-run legacy + unified; return legacy only; persist stage-level divergence diagnostics.

**Independent Test**: `RAG_PIPELINE_MODE=shadow` — HTTP response equals legacy-only; JSONL artifacts written (`quickstart.md` §3).

**Depends on**: US1 (legacy executor) + US4 (unified orchestrator).

### Tests for User Story 2

- [X] T047 [P] [US2] Integration test for shadow user-response parity in `tests/integration/test_shadow_mode.py`
- [X] T048 [P] [US2] Unit tests for shadow overlap and `first_divergent_stage` derivation in `tests/unit/services/rag/pipeline/test_shadow_diagnostics.py`

### Implementation for User Story 2

- [X] T049 [US2] Implement `ShadowComparisonStore` JSONL writer in `src/services/rag/pipeline/shadow_store.py`
- [X] T050 [US2] Implement overlap calculators (`retrieval_overlap`, `evidence_overlap`, `plan_strategy_match`) in `src/services/rag/pipeline/shadow_diagnostics.py`
- [X] T051 [US2] Implement `ShadowRunner` with concurrent `asyncio.gather`, unified timeout, and legacy-wins response in `src/services/rag/pipeline/shadow_runner.py`
- [X] T052 [US2] Wire shadow branch in `src/services/rag/pipeline/router.py` delegating to `ShadowRunner`
- [X] T053 [US2] Increment `rag_shadow_divergence_total` when `ShadowComparisonRecord.diverged=true`

**Checkpoint**: Shadow mode ready for 7-day staging validation.

---

## Phase 7: User Story 5 — Offline Quality Gating (Priority: P3)

**Goal**: Golden tests and regression diff validate unified pipeline before/during rollout.

**Independent Test**: Run 014 fixtures against unified path; produce `EvaluationResult` with pass/fail gate (`quickstart.md` §6).

### Tests for User Story 5

- [X] T054 [P] [US5] Integration test for unified golden run in `tests/integration/test_pipeline_golden_quality.py`
- [X] T055 [P] [US5] Integration test for baseline capture and regression diff in `tests/integration/test_pipeline_regression.py`

### Implementation for User Story 5

- [X] T056 [US5] Implement `PipelineSnapshot` builder from `UnifiedPipelineResult` in `src/services/rag/pipeline/snapshot_builder.py` for 014 `IGoldenTestRunner` consumption
- [X] T057 [US5] Add CLI/script `scripts/run_unified_golden_eval.py` executing golden fixtures through unified orchestrator and emitting `EvaluationResult` JSON
- [X] T058 [US5] Add nightly shadow aggregation script `scripts/aggregate_shadow_reports.py` summarizing divergence rates and stage breakdowns from JSONL
- [X] T059 [US5] Document CI gate thresholds in `specs/015-unified-pipeline-migration/quickstart.md` §6 (baseline save/compare commands)

**Checkpoint**: CI can gate merges on unified golden pass rate.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Observability, health, docs, and rollout readiness across all stories.

- [X] T060 [P] Expose optional `rag_pipeline` readiness block on existing health route in `src/routes/base.py` per `contracts/orchestrator.md`
- [X] T061 [P] Add integration test for startup fail-fast when retriever capabilities missing in `tests/integration/test_pipeline_startup.py`
- [X] T062 [P] Add integration test for unified fallback-on-error in `tests/integration/test_pipeline_fallback.py`
- [X] T063 [P] Add integration test for parser-preservation hash parity in `tests/integration/test_parser_parity.py`
- [X] T064 Update `src/ARCHITECTURE.md` with unified pipeline router diagram and mode table
- [X] T065 [P] Add `.rag_shadow/` to `.gitignore`
- [X] T066 Run full `quickstart.md` validation checklist and record results in `specs/015-unified-pipeline-migration/quickstart-results.json`

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
    └── Phase 2 (Foundational) — BLOCKS all user stories
            ├── Phase 3 (US1) ── MVP
            ├── Phase 4 (US3) ── depends on US1 router
            ├── Phase 5 (US4) ── depends on Foundational
            │       └── Phase 6 (US2) ── depends on US1 + US4
            └── Phase 7 (US5) ── depends on US4
                    └── Phase 8 (Polish) — depends on desired stories complete
```

### User Story Dependencies

| Story | Priority | Depends on | Blocks |
|-------|----------|------------|--------|
| US1 | P1 | Foundational | US3, US2 (partial) |
| US3 | P1 | US1 | — |
| US4 | P2 | Foundational | US2, US5 |
| US2 | P1 | US1 + US4 | — |
| US5 | P3 | US4 | — |

### Within Each User Story

- Tests written first (must fail before implementation)
- Models/types before services
- Adapters before orchestrator (US4)
- Router wiring after executors
- Story checkpoint before next priority

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 in parallel after T001
- **Phase 2**: T005–T015 mostly parallel (distinct files)
- **US1 tests**: T016, T017 parallel
- **US4 adapters**: T030–T036 parallel after T029
- **US2 + US5 tests**: parallel once US4 complete
- **Polish**: T060–T063 parallel

---

## Parallel Example: User Story 4 Adapters

```bash
# Launch all retriever adapters together (after T029):
T031: PgVectorDenseRetriever in src/services/rag/adapters/vector_retriever.py
T032: PgVectorSparseRetriever in src/services/rag/adapters/sparse_retriever.py
T033: StructuredInteractionRetriever in src/services/rag/adapters/interaction_retriever.py
T034: LegacyRerankerAdapter in src/services/rag/adapters/reranker_adapter.py
T035: SqlChunkReader in src/services/rag/adapters/chunk_reader.py
T036: EmbeddingProviderAdapter in src/services/rag/adapters/embedding_provider.py
```

---

## Parallel Example: Foundational Layer

```bash
# After T001–T004 complete, launch in parallel:
T005: models.py
T007: mode_resolver.py
T008: query_parse_service.py
T009: type_mapping.py
T010: response_adapter.py
T011: metrics.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: Contract + legacy integration tests pass
5. Deploy with `RAG_PIPELINE_MODE=legacy` (zero behavior change)

### Incremental Delivery

1. Setup + Foundational → shared types ready
2. US1 → legacy via router (MVP, production-safe)
3. US3 → rollback verified
4. US4 → unified callable behind flag
5. US2 → shadow in staging
6. US5 → CI golden gate
7. Polish → production cutover readiness

### Recommended Production Rollout (from plan.md)

| Week | Mode | Tasks complete through |
|------|------|------------------------|
| 1 | `legacy` | US1 + US3 |
| 2–3 | `shadow` | US2 + US4 |
| 4 | canary | US5 CI gate |
| 5+ | `unified` | Polish + monitoring |

### Parallel Team Strategy

With two developers after Foundational:

- **Dev A**: US1 → US3 → router polish
- **Dev B**: US4 adapters → US4 orchestrator → composition
- **Merge**: US2 shadow integration
- **Either**: US5 golden CI + polish

---

## Notes

- Phase 4 legacy removal (plan.md C1–C7) is **out of scope** — no tasks generated
- Search/index endpoints remain on legacy retrieval — do not migrate in this task list
- All tasks include explicit file paths for LLM execution without extra context
- Commit after each checkpoint; default production flag remains `legacy` until US2 validation completes

---

## Task Summary

| Phase | Story | Task IDs | Count |
|-------|-------|----------|-------|
| 1 Setup | — | T001–T004 | 4 |
| 2 Foundational | — | T005–T015 | 11 |
| 3 US1 API | US1 | T016–T022 | 7 |
| 4 US3 Rollback | US3 | T023–T026 | 4 |
| 5 US4 Unified | US4 | T027–T046 | 20 |
| 6 US2 Shadow | US2 | T047–T053 | 7 |
| 7 US5 Quality | US5 | T054–T059 | 6 |
| 8 Polish | — | T060–T066 | 7 |
| **Total** | | **T001–T066** | **66** |

**MVP scope**: Phase 1 + Phase 2 + Phase 3 (US1) = 22 tasks

**Format validation**: All tasks use `- [ ] [TaskID] [P?] [Story?] Description with file path`
