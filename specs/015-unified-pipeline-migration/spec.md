# Feature Specification: Unified Production Pipeline Migration

**Feature Branch**: `015-unified-pipeline-migration`

**Created**: 2026-07-15

**Status**: Draft

**Input**: Replace legacy RAG execution path with one unified production pipeline integrating specs 009–014 while preserving Query Parser (004), backward compatibility, feature-flag migration, shadow mode, rollback, and unchanged API contract.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamless API for existing clients (Priority: P1)

An API consumer continues calling `POST /api/v1/nlp/{project_id}/answer` with the same
request body and receives the same response shape (`signal`, `answer`, `needs_clarification`,
`full_prompt`, `chat_history`) regardless of which internal pipeline executes.

**Why this priority**: Zero client migration cost is the primary production constraint.

**Independent Test**: Send identical `AnswerRequest` payloads against legacy and unified
modes; assert response schema and HTTP status codes match.

**Acceptance Scenarios**:

1. **Given** `RAG_PIPELINE_MODE=legacy`, **When** a valid question is asked, **Then** the
   response matches current production behavior and schema.
2. **Given** `RAG_PIPELINE_MODE=unified`, **When** the same question is asked, **Then** the
   response schema is identical (field names, types, signal enum values).
3. **Given** any pipeline mode, **When** no index exists, **Then** HTTP 400 with
   `RAG_NO_CONTEXT` signal is returned unchanged.

---

### User Story 2 - Safe rollout with shadow mode (Priority: P1)

An operator enables shadow mode so the unified pipeline runs in parallel with legacy on
every request, but only the legacy answer is returned to the user. Divergence is logged and
recorded for offline review.

**Why this priority**: De-risks integration of six isolated modules before user-facing cutover.

**Independent Test**: Enable shadow mode; verify user response equals legacy-only output while
shadow comparison artifacts are persisted.

**Acceptance Scenarios**:

1. **Given** `RAG_PIPELINE_MODE=shadow`, **When** a question is answered, **Then** the HTTP
   response body equals what legacy mode would return.
2. **Given** shadow mode, **When** unified and legacy produce different answers, **Then** a
   structured shadow diff record is written with correlation id.
3. **Given** unified pipeline failure in shadow mode, **When** legacy succeeds, **Then** the
   user still receives a successful legacy answer.

---

### User Story 3 - Instant rollback (Priority: P1)

An operator flips a configuration flag to revert all traffic to the legacy pipeline without
redeploying code.

**Why this priority**: Production safety requirement for a high-risk architectural change.

**Independent Test**: Switch `RAG_PIPELINE_MODE` from `unified` to `legacy` at runtime;
confirm next request uses legacy path.

**Acceptance Scenarios**:

1. **Given** unified mode in production, **When** flag is set to `legacy`, **Then** the
   next request executes the legacy path exclusively.
2. **Given** rollback, **When** measured over 100 requests, **Then** zero requests invoke
   unified pipeline stages (verified via metrics/logs).

---

### User Story 4 - Unified pipeline delivers spec-quality answers (Priority: P2)

When unified mode is active, a question flows through Retrieval Planner → Retrieval Engine →
Evidence Orchestrator → Context Builder → Answer Generation, preserving Query Parser output
as the planner input.

**Why this priority**: Delivers the business value of specs 009–013 to real traffic.

**Independent Test**: Enable unified mode; assert stage traces show all five modules invoked
and `AnswerResult` carries `plan_id` and `context_id`.

**Acceptance Scenarios**:

1. **Given** unified mode, **When** a factual question is asked, **Then** pipeline trace
   includes planner, engine, orchestrator, context builder, and answer generation stages.
2. **Given** unified mode, **When** parser returns `needs_clarification=true`, **Then** the
   API returns clarification without invoking retrieval stages (same as legacy).
3. **Given** unified mode, **When** zero evidence is retrieved, **Then** a no-context answer
   is returned with the same user-facing semantics as legacy.

---

### User Story 5 - Offline quality gating (Priority: P3)

CI and operators run golden tests (spec 014) against unified pipeline snapshots to detect
regressions before and during rollout.

**Why this priority**: Validates quality without blocking initial architecture work.

**Independent Test**: Run golden fixture set against unified pipeline; produce
`EvaluationResult` with pass/fail gate.

**Acceptance Scenarios**:

1. **Given** golden fixtures, **When** unified pipeline is executed offline, **Then**
   `EvaluationResult.passed` reflects configured thresholds.
2. **Given** a baseline run, **When** a new commit is evaluated, **Then** `RegressionDiff`
   highlights score drops above threshold.

---

### Edge Cases

- Unified pipeline timeout or unhandled exception → fall back to legacy when
  `RAG_PIPELINE_FALLBACK_ON_ERROR=true` (default in canary phases).
- Shadow mode with legacy failure but unified success → log anomaly; return legacy error
  (user-visible behavior unchanged).
- Per-project override: project `config_json.pipeline_mode` overrides global default.
- Search endpoint (`/index/search`) remains on legacy retrieval until a follow-up spec;
  only answer path is in scope for v1 migration.
- Domain-specific branches (e.g. `interactions` field) must be expressed as planner
  strategies or adapter hooks, not hardcoded in the orchestrator.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST preserve `core.query_parser` (spec 004) as the first stage for
  both legacy and unified paths; parser output (`ParseResult`) MUST NOT be duplicated.
- **FR-002**: Unified path MUST invoke, in order: Retrieval Planner (009) → Retrieval Engine
  (010) → Evidence Orchestrator (011) → Context Builder (012) → Answer Generation (013).
- **FR-003**: HTTP API contract for `POST .../answer` MUST remain unchanged (request schema,
  response schema, status codes, signal enum values).
- **FR-004**: System MUST support `RAG_PIPELINE_MODE` with values `legacy`, `shadow`, and
  `unified`.
- **FR-005**: In `shadow` mode, system MUST execute both pipelines and return only the legacy
  response to the client.
- **FR-006**: System MUST support rollback to `legacy` via configuration change without code
  redeploy (environment variable and optional per-project override).
- **FR-007**: Infrastructure adapters MUST wrap existing `vectordb_client`, `embedding_client`,
  `generation_client`, `reranker`, and `chunk_repository` without modifying provider SDKs.
- **FR-008**: Unified path MUST map `AnswerResult` to the legacy return tuple
  `(answer, full_prompt, chat_history, needs_clarification)` via a response adapter.
- **FR-009**: System MUST emit structured logs and Prometheus metrics at each pipeline stage
  boundary with shared `request_id` / `project_id` correlation.
- **FR-010**: Shadow mode MUST persist comparison records (answer diff, citation diff, latency
  delta, stage outcome) for offline analysis.
- **FR-011**: Answer Quality (014) MUST integrate as an offline/shadow evaluation layer, not
  inline blocking of user requests in v1.
- **FR-012**: Legacy code path MUST remain callable until Phase 4 cleanup; no deletion in
  initial migration phases.
- **FR-013**: `PipelineExecutionContext` MUST be immutable after router entry and MUST carry
  `locale`, `deadline_at`, `pipeline_version`, and `settings_snapshot`.
- **FR-014**: Unified/shadow-unified execution MUST honor `ctx.deadline_at`; semantic outcomes
  (`no_context`, `clarification`) MUST NOT trigger legacy fallback.
- **FR-015**: `asyncio.CancelledError` MUST propagate without legacy fallback.
- **FR-016**: Shadow records MUST include stage-level diagnostics (`first_divergent_stage`,
  `retrieval_overlap`, `evidence_overlap`) when unified completes.
- **FR-017**: Startup MUST fail fast when `RAG_PIPELINE_MODE` is `unified` or `shadow` and
  required retriever capabilities are missing.

### Key Entities

- **PipelineMode**: Execution selector (`legacy` | `shadow` | `unified`).
- **PipelineExecutionContext**: Correlation ids, project, profile, settings snapshot.
- **UnifiedPipelineResult**: Internal aggregate (`ParseResult`, `RetrievalPlan`,
  `RetrievalResult`, `EvidencePack`, `Context`, `AnswerResult`, stage traces).
- **ShadowComparisonRecord**: Dual-run diff artifact for observability.
- **PipelineStageTrace**: Per-stage latency, outcome, and identifier (`plan_id`, etc.).

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Clean Architecture — orchestration in `services/rag/`; stage logic stays in
  `core/`; adapters in `services/rag/adapters/` or `stores/` implementing core protocols.
- **NFR-002**: Async-first — unified orchestrator is fully async; shadow dual-run uses
  `asyncio.gather` with timeout budgets.
- **NFR-003**: Pluggable providers — no new provider imports inside `core/*` pipelines.
- **NFR-004**: Citations — unified path returns traceable citations in `AnswerResult`; API
  adapter preserves any citation exposure legacy clients expect.
- **NFR-005**: Testing — contract tests for API; integration tests per pipeline mode; golden
  tests via spec 014 fixtures.
- **NFR-006**: Observability — extend existing `utils/metrics.py` histograms for unified
  stages; shadow divergence counter.
- **NFR-007**: Performance — shadow mode p95 latency overhead SHOULD be ≤ 2× legacy p95 during
  canary; unified-only mode SHOULD target ≤ 1.5× legacy p95 after optimization phase.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `/answer` responses match the existing JSON schema across all three
  pipeline modes (validated by contract tests).
- **SC-002**: Shadow mode runs for ≥ 7 days in staging with < 5% unhandled unified failures
  before canary promotion.
- **SC-003**: Golden test pass rate in unified mode is ≥ baseline legacy pass rate minus 5%
  before production cutover.
- **SC-004**: Rollback drill completes in < 5 minutes (flag flip + verification) with zero
  deploy.
- **SC-005**: After Phase 3 cutover, ≥ 95% of production answer traffic executes unified
  pipeline with legacy available as fallback.

## Assumptions

- Specs 009–013 module code is functionally complete for unit-level contracts; integration
  gaps (stub retrievers, registry config ignored) are addressed during adapter wiring, not
  re-specified here.
- Spec 008 (Knowledge Representation) is out of scope for v1 unified path; may attach in a
  follow-up once a consumer exists.
- Search/index endpoints remain on legacy retrieval in v1; only the answer orchestration
  path migrates.
- Per-project `pipeline_mode` override lives in existing `project.config_json` without a DB
  migration.
- Feature flag defaults to `legacy` until Phase 2 shadow validation completes.

## Out of Scope (v1)

- Implementation code (this spec defines architecture only).
- Deleting `core/retrieval/` legacy module (Phase 4).
- Migrating `/index/search` to Retrieval Engine.
- Inline Answer Quality gating on live requests.
- Knowledge Representation (008) ingestion wiring.
