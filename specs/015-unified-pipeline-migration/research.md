# Research: Unified Production Pipeline Migration

**Date**: 2026-07-15 | **Feature**: 015-unified-pipeline-migration

## R-001: Pipeline mode selection mechanism

**Decision**: Environment variable `RAG_PIPELINE_MODE` with optional per-project override in
`project.config_json.pipeline_mode`. Optional allowlist `RAG_PIPELINE_CANARY_PROJECT_IDS` for
canary phase.

**Rationale**: Matches existing configuration patterns in `helpers/config.py` (`RAG_ENABLE_*`
flags). Per-project override enables canary without separate deployment. Constitution requires
config-driven provider selection (G5).

**Alternatives considered**:

- *Feature flag service (LaunchDarkly)* — rejected: adds external dependency; team already
  uses env-based settings.
- *Database feature_flags table* — rejected for v1: requires migration and admin UI; JSON
  project override sufficient for canary.
- *Header-based mode override* — rejected: security risk; clients could force experimental path.

---

## R-002: Shadow mode execution model

**Decision**: Concurrent dual-run with `asyncio.gather(..., return_exceptions=True)`; legacy
result returned to client; unified result compared offline. Unified path subject to
`RAG_PIPELINE_UNIFIED_TIMEOUT_S`.

**Rationale**: Minimizes added latency vs sequential run while bounding tail risk. Returning
legacy preserves user trust during validation (ARCHITECTURE_AUDIT ARCH-01 recommendation).

**Alternatives considered**:

- *Sequential (legacy first, then unified async fire-and-forget)* — rejected: delays shadow
  data completeness on errors.
- *Sampled shadow (1% traffic)* — acceptable as optional cost control but not default; full
  shadow in staging, sampled in prod if needed.
- *Kafka event bus for shadow* — rejected for v1: over-engineered; file/JSON persistence enough.

---

## R-003: Shadow artifact storage

**Decision**: Append JSON lines to `RAG_PIPELINE_SHADOW_DIR/{YYYY-MM-DD}/comparisons.jsonl`
with fields defined in `data-model.md::ShadowComparisonRecord`.

**Rationale**: Zero schema migration; compatible with log shipping; easy nightly aggregation.
Aligns with 014 regression store pattern (file-based runs).

**Alternatives considered**:

- *PostgreSQL shadow_comparisons table* — deferred: useful for querying at scale; add in Phase 2
  if JSONL volume exceeds ops comfort.
- *Prometheus-only* — rejected: insufficient for answer text diff forensics.

---

## R-004: Type mapping between legacy and SpecKit models

**Decision**: Single module `services/rag/adapters/type_mapping.py` owning conversions:

- `RetrievedDocument` ↔ `RawCandidate` / `EvidenceItem`
- Legacy local `RetrievalResult` (dataclass in answer_service) ≠ `core.retrieval_engine.models.RetrievalResult` — rename legacy to `LegacyRetrievalOutcome` during migration prep (implementation phase); unified path uses engine type exclusively.

**Rationale**: ARCHITECTURE_AUDIT identifies duplicate `RetrievalResult` as integration hazard.
Central mapper prevents drift.

**Alternatives considered**:

- *Unify types globally upfront* — rejected: too large a blast radius; adapter isolation is
  smaller diff.
- *Dict-shaped duck typing* — rejected: violates constitution G4 type safety.

---

## R-005: Domain-specific retrieval hooks (interactions field)

**Decision**: Implement `StructuredInteractionRetriever` as an `IRetriever` registered for
strategy `structured_interaction`; planner strategy selector routes `field=interactions` to
this strategy via field-pack YAML extension (`retrieval.strategies.interactions`).

**Rationale**: Removes hardcoded branch in `answer_service.py` (ARCH-02) without embedding
pharmacy logic in orchestrator. Keeps domain rules in field packs.

**Alternatives considered**:

- *Keep hardcoded branch in orchestrator* — rejected: violates generic core principle.
- *Defer interactions to Phase 4* — rejected: would block parity for pharmacy projects.

---

## R-006: Registry configuration wiring

**Decision**: Refactor composition root to pass `RetrievalEngineConfig`, `EvidenceOrchestratorConfig`,
etc. from field-pack YAML slices into registry `build_*` methods; reject `_ = config` discard
pattern found in `EvidenceOrchestratorRegistry`.

**Rationale**: ARCHITECTURE_AUDIT ARCH-05; without config-driven registries, A/B of compressors/
scorers requires code changes.

**Alternatives considered**:

- *Hardcode defaults in factory* — rejected: blocks experimentation and pack overrides.
- *New registry framework* — rejected: extend existing registries minimally.

---

## R-007: Query Parser integration point

**Decision**: Extract parser invocation from `RAGService._run_parse_stage` into shared
`QueryParseService` used by both `LegacyPipelineExecutor` and `UnifiedRagOrchestrator`.
Single code path for catalog loading, conversation context, and `semantic_parse_async`.

**Rationale**: FR-001 requires parser preservation without duplication. Current parser logic
is embedded in 960-line `answer_service.py`.

**Alternatives considered**:

- *Unified orchestrator calls RAGService for parse only* — rejected: couples unified to legacy
  service.
- *Duplicate parse logic* — rejected: guaranteed drift.

---

## R-008: Fallback on unified failure

**Decision**: `RAG_PIPELINE_FALLBACK_ON_ERROR=true` by default in Phase 2–3. On unified
exception or timeout, log `pipeline_fallback_total{reason}`, execute legacy, return legacy
response.

**Rationale**: Production safety during canary. Rollback flag remains coarse override; fallback
is per-request safety net.

**Alternatives considered**:

- *Fail request on unified error* — rejected: bad UX during canary.
- *Silent empty answer* — rejected: violates API error semantics.

---

## R-009: Answer Quality (014) attachment point

**Decision**: Offline only in v1:

- CI golden runner executes full unified pipeline → 014 evaluators.
- Shadow nightly job optionally pipes `ShadowComparisonRecord` into faithfulness/coverage
  scorers when unified artifacts present.

**Rationale**: User request focuses on pipeline integration; inline gating adds latency and
product policy decisions not specified.

**Alternatives considered**:

- *Inline faithfulness block* — deferred to future spec.
- *Skip 014 entirely* — rejected: best regression strategy available in codebase.

---

## R-010: NLPController responsibility split

**Decision**:

- `NLPController` retains indexing, search, collection management (legacy retrieval).
- `answer_rag_question` delegates exclusively to `PipelineRouter` (injected factory).
- `UnifiedRagOrchestrator` does NOT call `NLPController.search_vector_db_collection`.

**Rationale**: Clear boundary: indexing/search stays legacy until follow-up; answer path uses
engine retrievers only. Prevents accidental hybrid of two stacks in one request.

**Alternatives considered**:

- *Engine calls NLPController for retrieval* — rejected: perpetuates dual-stack coupling.
- *Move search to engine in v1* — out of scope per spec.

---

## R-011: Observability correlation

**Decision**: Generate `pipeline_request_id` (UUID) at router entry; pass through all stage
traces; include in logs and shadow records. Extend Prometheus:

- `rag_pipeline_requests_total{mode, outcome}`
- `rag_pipeline_stage_duration_seconds{stage, mode}`
- `rag_shadow_divergence_total{severity}`

**Rationale**: Constitution G7; required for shadow analysis and rollback verification.

**Alternatives considered**:

- *Reuse session_id only* — rejected: session may be null; not unique per request.

---

## R-012: DI composition location

**Decision**: New `services/rag/composition.py` with `build_rag_pipeline_factory(app)` called
from `main.py` startup. Factory cached on `app.rag_pipeline_factory`.

**Rationale**: Keeps `main.py` readable; mirrors `get_field_registry()` pattern; testable in
isolation with mock app.

**Alternatives considered**:

- *Inline all wiring in main.py* — rejected: ~150 lines of registry wiring clutters entrypoint.
- *Separate DI container library* — rejected: over-engineering for FastAPI attribute pattern.

---

## Resolved Clarifications

All Technical Context items resolved. No remaining `NEEDS CLARIFICATION` markers.

---

## R-013: Pipeline execution lifecycle formalization

**Decision**: Add `StageStatus` enum and failure-propagation table to `data-model.md`; map
semantic outcomes separately from infrastructure failures.

**Rationale**: Existing early-exit diagram did not normatively define fallback vs no-fallback
paths — a common production incident source during canary.

**Alternatives considered**:

- *Full FSM library / state persistence* — rejected: unnecessary complexity for synchronous
  request scope.

---

## R-014: Request cancellation vs timeout

**Decision**: Router owns `deadline_at`; timeout may fallback; `CancelledError` always
re-raises without fallback or shadow persist.

**Rationale**: Client disconnect is not an infrastructure fault; fallback would waste resources
and conflate metrics.

**Alternatives considered**:

- *Unified cancellation token passed to all stages* — rejected for v1: deadline check at
  stage entry is sufficient.

---

## R-015: PipelineExecutionContext enrichment

**Decision**: Add `locale`, `deadline_at`, `pipeline_version`, `settings_snapshot`. Reject
per-module `planner_version` on context — use stage `detail.schema_version` instead.

**Rationale**: Shadow reproducibility and post-mortems need frozen flags; module versions belong
on stage artifacts.

---

## R-016: Retry ownership

**Decision**: No cross-stage retries; optional single-call retries inside adapters only.

**Rationale**: Orchestrator retries multiply tail latency and duplicate LLM cost; existing
provider clients already own generation retries.

---

## R-017: Adapter capabilities

**Decision**: Static `AdapterCapabilities.features` frozenset; startup validation only.

**Rationale**: Prevents silent "registered but no-op" retrievers (ARCHITECTURE_AUDIT stub risk)
without a dynamic discovery protocol.

---

## R-018: Shadow stage diagnostics

**Decision**: Add overlap metrics and `first_divergent_stage` to `ShadowComparisonRecord`.

**Rationale**: Answer-only diff insufficient to localize retrieval vs generation regressions.

**Alternatives considered**:

- *Full context text diff* — rejected: PII and storage cost.

---

## R-019: Phase 4 cleanup gates

**Decision**: Seven measurable exit criteria (C1–C7) with 30-day production window.

**Rationale**: Phase 4 was deferred without objective removal gates — risks premature legacy deletion.
