# Tasks: Production Scalability & Reliability

**Input**: Design documents from `/specs/017-scalability-reliability/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required per constitution (Principle VII) — unit, contract, and integration tests included for each user story.

**Organization**: Tasks grouped by user story for independent implementation and testing. Hardens the sole ingest path (016 M0) — no parallel ingest stack.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US6)

## Path Conventions

- Source: `src/`
- Tests: `tests/contract/`, `tests/integration/ingestion/`, `tests/unit/services/ingest_reliability/`, `tests/unit/core/`
- Migrations: `src/models/db_schemes/algorag/alembic/versions/`
- Schemes: `src/models/db_schemes/algorag/schemes/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package layout, settings surface, and env documentation for ingest reliability control plane.

- [X] T001 Create package `src/services/ingest_reliability/` with `__init__.py` exporting package version constant `INGEST_RELIABILITY_VERSION = "1.0.0"`
- [X] T002 [P] Create package `src/services/ingest_reliability/stages/` with `__init__.py` for stage contract helpers
- [X] T003 [P] Add ingest reliability settings to `src/helpers/config.py` (feature flags, workload budgets, stall/timeout policy knobs, canary project ids, operational mode override) — values validated; no hard-coded device-specific production numbers beyond safe defaults
- [X] T004 [P] Document new env vars in `src/.env.example` with comments pointing to `specs/017-scalability-reliability/data-model.md`
- [X] T005 [P] Create test package dirs `tests/unit/services/ingest_reliability/__init__.py`, `tests/integration/ingestion/__init__.py`, and `tests/contract/test_ingest_lifecycle.py` placeholder module docstring only

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Durable job control plane, lifecycle, history, capacity claims, metrics, and admission hook — required before any user story.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T006 [P] Implement Pydantic domain enums/models (`LifecycleState`, `ParseOutcomeClass`, `FailureOwnership`, `WorkloadClass`, `ProgressKind`, `OperationalMode`, `ComponentHealthState`) in `src/services/ingest_reliability/models.py` per `data-model.md` and `contracts/job-lifecycle.md`
- [X] T007 [P] Implement SQLAlchemy scheme `IngestJob` in `src/models/db_schemes/algorag/schemes/ingest_job.py` (job_id, correlation_id, project_id, logical document identity/version, lifecycle_state, workload_class, progress fields, checkpoint_ref, publish_completion_id, configuration_version, timestamps)
- [X] T008 [P] Implement SQLAlchemy schemes for `IngestOperationalEvent`, `IngestCheckpoint`, `IngestCapacityClaim`, `LogicalDocumentVersion`, `PublishCompletion` in `src/models/db_schemes/algorag/schemes/ingest_control_plane.py`
- [X] T009 Register new schemes in `src/models/db_schemes/algorag/schemes/__init__.py`
- [X] T010 Create Alembic migration adding ingest control-plane tables in `src/models/db_schemes/algorag/alembic/versions/` (unique publish completion on identity+version; indexes on correlation_id, lifecycle_state, project_id)
- [X] T011 Implement lifecycle transition guard `transition_job(job, new_state, cause)` in `src/services/ingest_reliability/lifecycle.py` enforcing terminal irreversibility and Publishing-only publish entry per `contracts/job-lifecycle.md`
- [X] T012 [P] Implement operational history appender `append_event(...)` in `src/services/ingest_reliability/history.py` (no secrets; always includes correlation_id)
- [X] T013 [P] Implement capacity claim hold/release helpers in `src/services/ingest_reliability/capacity.py` per `contracts/admission-capacity.md`
- [X] T014 [P] Add ingest reliability metrics to `src/utils/metrics.py` (admission outcomes, stage duration, parse outcomes, progress/stall, publish completions, capacity claim leaks, orphan recoveries)
- [X] T015 Implement `IngestJobService` create/get/update by job_id and correlation_id in `src/services/ingest_reliability/job_service.py`
- [X] T016 Wire job creation + correlation_id into `src/routes/data.py` `process_endpoint` and `process_and_push_endpoint` so acceptance returns trackable job identity without breaking existing response fields (additive)
- [X] T017 [P] Unit tests for lifecycle transitions in `tests/unit/services/ingest_reliability/test_lifecycle.py`
- [X] T018 [P] Unit tests for capacity claim hold/release in `tests/unit/services/ingest_reliability/test_capacity.py`
- [X] T019 [P] Unit tests for history append sanitization in `tests/unit/services/ingest_reliability/test_history.py`

**Checkpoint**: Foundation ready — stories can attach stage behavior to durable jobs.

---

## Phase 3: User Story 1 — Large Documents Without Collapse (Priority: P1) 🎯 MVP

**Goal**: Large documents process in bounded units under workload-class budgets without starving small-document work or collapsing the service.

**Independent Test**: Submit a large-document-profile fixture under concurrent small-doc load; large job reaches terminal state within budget; small docs still progress (`quickstart.md` Scenario B partial — without resume yet).

### Tests for User Story 1

- [X] T020 [P] [US1] Unit tests for workload-class budget selection in `tests/unit/services/ingest_reliability/test_workload_budgets.py`
- [ ] T021 [P] [US1] Integration test: large + small concurrent ingest memory/progress sanity in `tests/integration/ingestion/test_large_document_bounded.py`

### Implementation for User Story 1

- [X] T022 [P] [US1] Implement workload class resolver + budget snapshot in `src/services/ingest_reliability/workload.py`
- [X] T023 [US1] Add bounded/streaming processing controls in `src/services/process_service.py` so peak memory follows workload budget (within hard max) rather than full-document materialization
- [X] T024 [US1] Propagate workload_class and progress updates (stage + coarse progress + `progressing`/`waiting`) through `src/tasks/file_processing.py` into `IngestJobService`
- [X] T025 [US1] Enforce hard size/duration gates before expensive work in `src/services/ingest_reliability/gates.py` (fail fast → `Failed`, ownership `user_input` or `document_quality`)
- [X] T026 [US1] Emit stage latency + resource-limit metrics from `src/tasks/file_processing.py` / `src/utils/metrics.py`

**Checkpoint**: MVP — large docs bounded; jobs observable through lifecycle states Accepted→…→terminal.

---

## Phase 4: User Story 2 — Overload & Back-Pressure (Priority: P1)

**Goal**: Burst load is delayed or rejected explicitly; accepted work stays within concurrency/backlog budgets.

**Independent Test**: Flood admission beyond limits; ≥99% excess get explicit delay/reject; no silent unbounded accept (`quickstart.md` Scenario E).

### Tests for User Story 2

- [X] T027 [P] [US2] Unit tests for admission decision matrix in `tests/unit/services/ingest_reliability/test_admission.py`
- [X] T028 [P] [US2] Contract tests for admission outcomes in `tests/contract/test_ingest_admission.py` per `contracts/admission-capacity.md`
- [ ] T029 [P] [US2] Integration test overload burst in `tests/integration/ingestion/test_admission_backpressure.py`

### Implementation for User Story 2

- [X] T030 [US2] Implement `AdmissionController.decide(...)` in `src/services/ingest_reliability/admission.py` (accept / delay / reject from available capacity + mode)
- [X] T031 [US2] Integrate admission decision into `src/routes/data.py` before Celery dispatch; return explicit capacity signal on delay/reject
- [X] T032 [US2] Implement inter-stage flow control hooks in `src/services/ingest_reliability/flow_control.py` and call from `src/tasks/file_processing.py` / indexing path so slow downstream regulates upstream
- [X] T033 [US2] Record admission metrics + history events (accept/delay/reject) via `src/services/ingest_reliability/history.py`

**Checkpoint**: Overload cannot silently enqueue unbounded work.

---

## Phase 5: User Story 3 — Parser Reliability (Priority: P1)

**Goal**: Parse outcomes classified success/degraded/failed; degraded publishes only after min-content gate; empty success forbidden.

**Independent Test**: Golden parse fixture matrix → expected terminal classes (`quickstart.md` Scenario A).

### Tests for User Story 3

- [X] T034 [P] [US3] Unit tests for parse outcome → lifecycle mapping in `tests/unit/services/ingest_reliability/test_parse_outcomes.py`
- [ ] T035 [P] [US3] Integration test degraded/fail matrix in `tests/integration/ingestion/test_parse_reliability_matrix.py`

### Implementation for User Story 3

- [X] T036 [US3] Map Document Intelligence extraction outcomes into `ParseOutcomeClass` + reason codes in `src/services/ingest_reliability/parse_bridge.py` (reuse `src/core/document_intelligence/` — no second parser stack)
- [X] T037 [US3] Drive lifecycle `Parsing` / `Degraded Parsing` transitions from `src/tasks/file_processing.py` via `lifecycle.py`
- [X] T038 [US3] Implement minimum usable-content + post-parse gates in `src/services/ingest_reliability/gates.py`; block success when no safe content (FR-010)
- [X] T039 [US3] Ensure terminal `Completed With Warnings` only when degraded publish later succeeds; otherwise `Failed` with ownership `document_quality`

**Checkpoint**: Parse classification is explicit and empty success is impossible.

---

## Phase 6: User Story 4 — Retry, Resume, Cancellation, Poison (Priority: P1)

**Goal**: Transient failures resume/retry idempotently; cancel/timeout cleanup; poison/dead-letter stop capacity hot-loops.

**Independent Test**: Crash/resume, cancel mid-flight, permanent failure exhaustion (`quickstart.md` Scenarios B, D, G).

### Tests for User Story 4

- [X] T040 [P] [US4] Unit tests for resume eligibility + retry class in `tests/unit/services/ingest_reliability/test_resume_retry.py`
- [X] T041 [P] [US4] Unit tests for poison threshold → quarantine in `tests/unit/services/ingest_reliability/test_poison.py`
- [ ] T042 [P] [US4] Integration test cancel/timeout reclaim in `tests/integration/ingestion/test_cancel_timeout.py`
- [ ] T043 [P] [US4] Integration test worker restart resume in `tests/integration/ingestion/test_checkpoint_resume.py`

### Implementation for User Story 4

- [X] T044 [P] [US4] Implement checkpoint commit/load API in `src/services/ingest_reliability/checkpoints.py`
- [X] T045 [US4] Write checkpoints from resumable points in `src/tasks/file_processing.py` and indexing path (`src/tasks/data_indexing.py` or equivalent)
- [X] T046 [US4] Implement cancel + timeout control in `src/services/ingest_reliability/cancellation.py`; transition to `Cancelled`/`Timed Out` only after cleanup; release capacity claims
- [X] T047 [US4] Expose operator cancel path (route or service method) from `src/routes/data.py` calling `cancellation.py`
- [X] T048 [US4] Classify transient vs permanent failures + ownership in `src/services/ingest_reliability/failures.py`; bound retries in Celery task options / job policy without unbounded loops
- [X] T049 [US4] Implement poison quarantine + dead-letter records in `src/services/ingest_reliability/poison.py` and persist via `ingest_control_plane.py` schemes
- [X] T050 [US4] Implement stall/no-progress detection + escalation to timeout in `src/services/ingest_reliability/progress.py` (FR-057)
- [X] T051 [US4] On cancel/timeout/fail paths, reclaim unpublished intermediate artifacts via `src/services/ingest_reliability/reclamation.py`

**Checkpoint**: Interruptions leave consistent searchable state and release capacity.

---

## Phase 7: User Story 5 — Atomic / Exactly-Once Publishing (Priority: P1)

**Goal**: Searchers see previous Active Version or fully published new version only; each version publishes exactly once.

**Independent Test**: Replacement V1→V2 visibility + post-success retry no-op (`quickstart.md` Scenario C).

### Tests for User Story 5

- [ ] T052 [P] [US5] Contract tests for publishing semantics in `tests/contract/test_ingest_publishing.py` per `contracts/publishing-semantics.md`
- [ ] T053 [P] [US5] Integration test atomic replacement visibility in `tests/integration/ingestion/test_atomic_publish.py`
- [ ] T054 [P] [US5] Integration test exactly-once after duplicate completion in `tests/integration/ingestion/test_exactly_once_publish.py`

### Implementation for User Story 5

- [X] T055 [P] [US5] Implement logical document version repository helpers in `src/services/ingest_reliability/versions.py` (active/superseded/preparing)
- [X] T056 [US5] Keep indexing materialization unpublished until publish stage in `src/tasks/data_indexing.py` (or dedicated publish step module `src/services/ingest_reliability/publish.py`)
- [X] T057 [US5] Implement integrity gates (content, searchable completeness, metadata, version consistency) in `src/services/ingest_reliability/gates.py` before activation
- [X] T058 [US5] Implement exactly-once `PublishCompletion` activation in `src/services/ingest_reliability/publish.py` (unique identity+version; duplicate completion → no-op)
- [X] T059 [US5] Drive lifecycle `Indexing` → `Publishing` → `Completed` / `Completed With Warnings` from workflow in `src/tasks/process_workflow.py` / indexing task
- [X] T060 [US5] Ensure failed/cancelled/timed-out jobs never flip Active Version; supersede prior only on successful publish

**Checkpoint**: Partial publish impossible; exactly-once activation holds under retry.

---

## Phase 8: User Story 6 — Observe, Audit, Modes, Orphans, Rollout (Priority: P2)

**Goal**: Full correlation-id history; operational modes; orphan recovery; staged rollout/rollback governance.

**Independent Test**: History reconstruction; mode behavior; orphan reclaim; canary promote/rollback drill (`quickstart.md` Scenarios F, H, I + observability checks).

### Tests for User Story 6

- [ ] T061 [P] [US6] Contract tests for observability/audit fields in `tests/contract/test_ingest_observability.py` per `contracts/observability-audit.md`
- [X] T062 [P] [US6] Unit tests for operational mode behavior in `tests/unit/services/ingest_reliability/test_operational_modes.py`
- [ ] T063 [P] [US6] Integration test orphan recovery after kill in `tests/integration/ingestion/test_orphan_recovery.py`
- [ ] T064 [P] [US6] Integration test canary enable/rollback in `tests/integration/ingestion/test_rollout_canary.py`
- [ ] T065 [P] [US6] Integration test dependency Unavailable containment in `tests/integration/ingestion/test_dependency_isolation.py`

### Implementation for User Story 6

- [X] T066 [P] [US6] Implement job status/history read API in `src/routes/data.py` (or `src/routes/projects.py`) returning lifecycle, gates, retries, failures, progress_kind by job_id/correlation_id
- [X] T067 [P] [US6] Implement component health registry + circuit gate helper in `src/services/ingest_reliability/health.py` per `contracts/operational-modes.md`
- [X] T068 [US6] Implement operational mode manager in `src/services/ingest_reliability/modes.py` (Normal/Degraded/Maintenance/Recovery/Admission Restricted) and consult from `admission.py`
- [X] T069 [US6] Implement orphan detector/reclaimer in `src/services/ingest_reliability/orphans.py` (jobs, checkpoints, intermediate artifacts) with defined recovery ownership outcomes
- [X] T070 [US6] Schedule or invoke orphan recovery on worker startup in `src/celery_runtime.py` (or equivalent worker boot hook)
- [X] T071 [US6] Implement service protection checks so maintenance/migration/background classes cannot consume interactive capacity in `src/services/ingest_reliability/capacity.py` / `workload.py`
- [X] T072 [US6] Add canary/cohort enablement + rollout config resolution in `src/services/ingest_reliability/rollout.py` and `src/helpers/config.py`
- [X] T073 [US6] Add security validation gates (authorization, tenant ownership, policy) before expensive work in `src/services/ingest_reliability/gates.py` and call from admission path
- [X] T074 [US6] Ensure configuration version recorded on each job and invalid config rejected in `src/services/ingest_reliability/config_safety.py`
- [X] T075 [US6] Align stage contract helper docstrings/assertions in `src/services/ingest_reliability/stages/contracts.py` with `contracts/stage-contracts.md`

**Checkpoint**: Operators can diagnose, recover, and roll out/back with evidence.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation, docs, and production readiness glue.

- [ ] T076 [P] Run and record `specs/017-scalability-reliability/quickstart.md` scenarios A–I into `specs/017-scalability-reliability/quickstart-results.json`
- [X] T077 [P] Add architecture note cross-links in `src/ARCHITECTURE.md` for ingest reliability control plane (sole-path; points to 017 contracts)
- [X] T078 Verify no second ingest stack / feature-flag permanent dual path; document sole-path cutover in `specs/017-scalability-reliability/plan.md` Complexity Tracking if any exception ADR needed (expect none)
- [ ] T079 [P] Soak/stress harness notes or script entrypoint under `scripts/` for concurrency-limit soak (SC-010) — documentation-first if automation deferred
- [ ] T080 Fill gaps from contract suite failures; ensure SC-018–SC-024 covered by automated or recorded drills

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US1 (Phase 3)**: After Foundational — MVP
- **US2 (Phase 4)**: After Foundational — can parallelize with US1 after T016 admission hook exists (prefer after US1 MVP if single-threaded)
- **US3 (Phase 5)**: After Foundational — integrates with parse path used by US1
- **US4 (Phase 6)**: After Foundational; benefits from US1 progress fields; cancel/publish cleanup must respect US5 rules when both land
- **US5 (Phase 7)**: After Foundational; should land before declaring US4 “done” for publish-safety under retry (recommend US5 before or immediately after US4 cancel paths touch publish)
- **US6 (Phase 8)**: After Foundational; strongest value after US1–US5 signals exist
- **Polish (Phase 9)**: After desired stories complete

### User Story Dependencies

| Story | Depends on | Independently testable? |
| ----- | ---------- | ----------------------- |
| US1 Large docs | Phase 2 | Yes — bounded processing + job progress |
| US2 Back-pressure | Phase 2 | Yes — admission matrix without large-doc fixtures |
| US3 Parse reliability | Phase 2 | Yes — fixture matrix on parse outcomes |
| US4 Resume/cancel/poison | Phase 2; publish-safe cleanup ↔ US5 | Yes for cancel/resume; exactly-once asserted with US5 |
| US5 Atomic publish | Phase 2 | Yes — replacement visibility suite |
| US6 Ops/rollout | Phase 2; richer with US1–US5 | Yes — history/mode/orphan/canary drills |

### Suggested sequencing (single implementer)

`Phase1 → Phase2 → US1 (MVP) → US2 → US3 → US5 → US4 → US6 → Polish`

(US5 before US4 reduces risk of resume/retry creating partial visibility.)

### Parallel Opportunities

- Phase 1: T002–T005 in parallel
- Phase 2: T006–T008, T012–T014, T017–T019 in parallel after models sketched
- Per story: all `[P]` tests in parallel; model/helper files marked `[P]` in parallel
- After Phase 2: US2 admission tests/impl can proceed beside US3 parse bridge if staffed

---

## Parallel Example: User Story 5

```bash
# Tests in parallel:
Task: "Contract tests for publishing semantics in tests/contract/test_ingest_publishing.py"
Task: "Integration test atomic replacement visibility in tests/integration/ingestion/test_atomic_publish.py"
Task: "Integration test exactly-once after duplicate completion in tests/integration/ingestion/test_exactly_once_publish.py"

# Then implementation:
Task: "Implement logical document version repository helpers in src/services/ingest_reliability/versions.py"
Task: "Implement exactly-once PublishCompletion activation in src/services/ingest_reliability/publish.py"
```

---

## Parallel Example: User Story 2

```bash
Task: "Unit tests for admission decision matrix in tests/unit/services/ingest_reliability/test_admission.py"
Task: "Contract tests for admission outcomes in tests/contract/test_ingest_admission.py"
Task: "Integration test overload burst in tests/integration/ingestion/test_admission_backpressure.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup  
2. Complete Phase 2: Foundational (CRITICAL)  
3. Complete Phase 3: US1 large-document bounded processing + job lifecycle visibility  
4. **STOP and VALIDATE** with `tests/integration/ingestion/test_large_document_bounded.py`  
5. Demo: large job terminal + small jobs still progress  

### Incremental Delivery

1. Setup + Foundational → control plane live  
2. US1 → MVP bounded large ingest  
3. US2 → production-safe overload behavior  
4. US3 → parse trustworthiness  
5. US5 → search consistency (atomic/exactly-once)  
6. US4 → operational interrupt safety (resume/cancel/poison)  
7. US6 → operability + rollout governance  
8. Polish → quickstart-results + soak evidence  

### Parallel Team Strategy

1. Team finishes Phase 1–2 together  
2. Then:  
   - Dev A: US1 + US3 (processing/parse)  
   - Dev B: US2 + capacity/flow control  
   - Dev C: US5 publish/versions  
   - Dev D: US4 interrupt/poison + US6 ops  

---

## Notes

- Do **not** create a second selectable ingest pipeline; extend `process_service` / Celery workflow only.
- Numeric budgets stay in validated settings (`FR-049` / research R18).
- Commit after each task or cohesive group; keep tests failing first where practical.
- Independent story tests map to `quickstart.md` scenarios A–I.
