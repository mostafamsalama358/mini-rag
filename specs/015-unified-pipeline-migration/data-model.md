# Data Model: Unified Production Pipeline Migration

**Date**: 2026-07-15 | **Source**: research.md + spec.md + plan.md

Models below are architectural contracts for the migration layer. Upstream types from specs
009–013 are consumed read-only; this spec defines orchestration-boundary types only.

---

## Configuration Models

### `PipelineMode`

```text
Literal["legacy", "shadow", "unified"]
```

Resolved by `PipelineModeResolver` (see contracts/orchestrator.md).

---

### `PipelineSettings` (extends app Settings slice)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `RAG_PIPELINE_MODE` | `PipelineMode` | `"legacy"` | Global default execution mode |
| `RAG_PIPELINE_FALLBACK_ON_ERROR` | `bool` | `true` | Per-request fallback to legacy on unified failure |
| `RAG_PIPELINE_SHADOW_PERSIST` | `bool` | `true` | Write shadow comparison artifacts |
| `RAG_PIPELINE_SHADOW_DIR` | `str` | `".rag_shadow/"` | Shadow artifact root directory |
| `RAG_PIPELINE_UNIFIED_TIMEOUT_S` | `float` | `45.0` | Timeout for unified path in shadow/gather |
| `RAG_PIPELINE_CANARY_PROJECT_IDS` | `str` | `""` | Comma-separated project ids forced to unified |
| `RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD` | `float` | `0.85` | Normalized answer similarity below = divergence |

Validation: `RAG_PIPELINE_UNIFIED_TIMEOUT_S` > 0; threshold in `[0.0, 1.0]`.

---

## Execution Context

### `PipelineExecutionContext`

Threaded through router and orchestrator for one `/answer` request. Created once at router
entry and treated as **immutable** after construction (frozen dataclass or Pydantic
`model_config = ConfigDict(frozen=True)`).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | `str` | ✅ | UUID correlation id |
| `project_id` | `int` | ✅ | Target project |
| `session_id` | `str \| None` | optional | Chat session |
| `mode` | `PipelineMode` | ✅ | Resolved execution mode |
| `profile` | `FieldProfile` | ✅ | Resolved field pack profile |
| `metadata_filter` | `dict \| None` | optional | Request-level pre-filter |
| `limit` | `int` | ✅ | Retrieval limit from request |
| `locale` | `str` | ✅ | BCP-47-ish language tag (e.g. `en`, `ar`); from query detection |
| `started_at` | `float` | ✅ | `time.perf_counter()` at router entry |
| `deadline_at` | `float` | ✅ | `started_at + effective_timeout_s`; unified/shadow-unified bound |
| `pipeline_version` | `str` | ✅ | Migration orchestrator version (e.g. `"1.0.0"`); not per-module |
| `settings_snapshot` | `PipelineSettingsSnapshot` | ✅ | Frozen pipeline flags effective for this request (see below) |

**Intentionally omitted** from context (available elsewhere — do not duplicate):

- `planner_version` / per-module versions — carried on stage configs (`schema_version`) and
  `PipelineStageTrace.detail`, not on the request context.
- Full `Settings` object — only pipeline-relevant flags are snapshotted.

---

### `PipelineSettingsSnapshot`

Immutable copy of pipeline flags resolved at request entry. Used for shadow reproducibility
and post-mortems when env changes mid-flight.

| Field | Type | Description |
|-------|------|-------------|
| `pipeline_mode` | `PipelineMode` | Resolved mode (mirrors `ctx.mode`) |
| `fallback_on_error` | `bool` | `RAG_PIPELINE_FALLBACK_ON_ERROR` |
| `unified_timeout_s` | `float` | Effective timeout for unified branch |
| `hybrid_search_enabled` | `bool` | `RAG_ENABLE_HYBRID_SEARCH` |
| `reranker_enabled` | `bool` | `RAG_ENABLE_RERANKER` |
| `semantic_parser_enabled` | `bool` | `RAG_SEMANTIC_PARSER_ENABLED` |

---

## Internal Pipeline Aggregate

### `UnifiedPipelineResult`

Output of `UnifiedRagOrchestrator` before API adaptation.

| Field | Type | Description |
|-------|------|-------------|
| `context` | `PipelineExecutionContext` | Request context |
| `parse_result` | `ParseResult` | From query_parser (004) |
| `retrieval_plan` | `RetrievalPlan \| None` | From planner (009); None if clarify/early exit |
| `retrieval_result` | `core.retrieval_engine.models.RetrievalResult \| None` | Engine output |
| `evidence_pack` | `EvidencePack \| None` | Orchestrator output |
| `context` | `Context \| None` | Context builder output |
| `answer_result` | `AnswerResult \| None` | Answer generation output |
| `stage_traces` | `list[PipelineStageTrace]` | Ordered stage telemetry |
| `outcome` | `PipelineOutcome` | Terminal status enum |

**Note**: Field name collision with `Context` (012) — in implementation, rename orchestration
wrapper field to `built_context: Context | None` to avoid shadowing.

---

### `PipelineOutcome`

```text
Literal[
  "success",
  "clarification",
  "no_context",
  "field_unavailable",
  "error",
  "timeout"
]
```

---

### `StageStatus`

Per-stage lifecycle within a single request (not persisted separately; carried on
`PipelineStageTrace.status`).

```text
pending → running → completed | failed | skipped | timed_out
```

| Status | Meaning |
|--------|---------|
| `pending` | Not yet started (optional; may omit and infer from trace order) |
| `running` | Stage in progress (optional; for in-flight diagnostics only) |
| `completed` | Stage finished successfully |
| `failed` | Stage raised a non-timeout, non-cancellation error |
| `skipped` | Stage not invoked (early exit or upstream failure) |
| `timed_out` | Stage or router deadline exceeded |

---

### `PipelineStageTrace`

| Field | Type | Description |
|-------|------|-------------|
| `stage` | `Literal["parse","plan","retrieve","evidence","context","answer"]` | Stage name |
| `status` | `StageStatus` | Terminal stage status |
| `started_at` | `float` | perf_counter |
| `duration_ms` | `float` | Stage wall time |
| `outcome` | `str` | **Deprecated alias** for `status`; prefer `status` in new code |
| `plan_id` | `str \| None` | Set from `RetrievalPlan.plan_id` when available |
| `context_id` | `str \| None` | Set from `Context.context_id` when available |
| `error_type` | `str \| None` | Exception class name on failure |
| `detail` | `dict \| None` | Stage-specific counts (candidates, items, tokens, `schema_version`) |

---

## Shadow Mode Models

### `ShadowComparisonRecord`

Persisted as JSONL when `RAG_PIPELINE_SHADOW_PERSIST=true`.

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | `str` | Correlation id |
| `project_id` | `int` | — |
| `mode` | `"shadow"` | Constant |
| `recorded_at` | `str` | ISO 8601 UTC |
| `query_text` | `str` | Original question (consider PII policy) |
| `legacy_outcome` | `PipelineOutcome` | — |
| `unified_outcome` | `PipelineOutcome` | — |
| `legacy_answer` | `str \| None` | Legacy answer text |
| `unified_answer` | `str \| None` | Unified answer text |
| `answer_similarity` | `float \| None` | Normalized similarity score |
| `diverged` | `bool` | `similarity < threshold` or outcome mismatch |
| `legacy_latency_ms` | `float` | Total legacy path |
| `unified_latency_ms` | `float \| None` | Total unified path |
| `unified_plan_id` | `str \| None` | For correlation with 014 eval |
| `legacy_citation_count` | `int` | Best-effort from legacy (may be 0 pre-migration) |
| `unified_citation_count` | `int` | From `AnswerResult.citations` |
| `unified_error` | `str \| None` | Error summary if unified failed |
| `first_divergent_stage` | `str \| None` | Earliest stage where legacy/unified paths materially differ (see below) |
| `plan_strategy_match` | `bool \| None` | Unified plan strategies align with legacy retrieval path classification |
| `retrieval_overlap` | `float \| None` | Jaccard similarity on chunk/doc ids (legacy docs vs engine candidates) |
| `evidence_overlap` | `float \| None` | Jaccard on `EvidencePack.items[*].doc_id` vs legacy doc ids |
| `context_token_delta` | `int \| None` | Unified context token count minus legacy prompt doc char proxy (approx) |

**`first_divergent_stage` derivation** (normative, evaluated in order):

1. Outcome mismatch (`legacy_outcome` ≠ `unified_outcome`) → earliest stage with differing
   `PipelineStageTrace.status` between paths, else `"answer"`.
2. Else `retrieval_overlap` < 0.5 → `"retrieve"`.
3. Else `evidence_overlap` < 0.5 → `"evidence"`.
4. Else `answer_similarity` below threshold → `"answer"`.
5. Else `null` (no material divergence).

Shadow comparison MUST NOT persist full context text or prompts by default (PII/size).

---

## API Boundary Models

### `PipelineAnswerResponse`

Internal representation before JSON serialization; maps 1:1 to current API.

| Field | Type | Maps to API field |
|-------|------|-------------------|
| `answer` | `str \| None` | `answer` |
| `full_prompt` | `str \| None` | `full_prompt` |
| `chat_history` | `list \| None` | `chat_history` |
| `needs_clarification` | `bool` | `needs_clarification` |
| `signal` | `ResponseSignal` | `signal` |

`ResponseAdapter` is the sole translator from `UnifiedPipelineResult` or legacy tuple to
this model.

---

## Upstream Types (read-only references)

| Type | Module | Role in unified path |
|------|--------|----------------------|
| `ParseResult` | `core.query_parser.schema` | Parser output → planner input |
| `RetrievalPlan` | `core.retrieval_planner.models` | Planner output → engine input |
| `RetrievalResult` | `core.retrieval_engine.models` | Engine output → orchestrator input |
| `EvidencePack` | `core.evidence_orchestrator.models` | Orchestrator output → context input |
| `Context` | `core.context_builder.models` | Context output → answer input |
| `AnswerResult` | `core.answer_generation.models` | Final scored artifact |

---

## State Transitions

```text
                    ┌─────────────┐
                    │   Router    │
                    │ resolve mode│
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐      ┌───────────┐     ┌──────────┐
    │ legacy  │      │  shadow   │     │ unified  │
    └────┬────┘      └─────┬─────┘     └────┬─────┘
         │                 │                 │
         │           legacy + unified        │
         │           (parallel)              │
         │                 │                 │
         └────────────┬────┴────────────────┘
                      ▼
              ResponseAdapter
                      ▼
              PipelineAnswerResponse
                      ▼
                 JSONResponse
```

### Unified stage state machine

```text
parse ──needs_clarification──► clarification (terminal)
  │
  ▼
plan ──clarify──► clarification (terminal)
  │
  ▼
retrieve ──empty──► no_context (terminal)
  │
  ▼
evidence ──empty pack──► no_context (terminal)
  │
  ▼
context ──empty blocks──► no_context (terminal)
  │
  ▼
answer ──► success | clarification
```

### Stage failure propagation (normative)

| Failed stage | `PipelineOutcome` | Later stages | Router action (unified mode) |
|--------------|-------------------|--------------|------------------------------|
| parse (error) | `error` | all `skipped` | Fallback if enabled; else 400 |
| parse (clarify) | `clarification` | all `skipped` | Return clarification (no fallback) |
| plan (error) | `error` | retrieve→answer `skipped` | Fallback if enabled |
| plan (clarify) | `clarification` | retrieve→answer `skipped` | Return clarification |
| retrieve (error/timeout) | `error` / `timeout` | evidence→answer `skipped` | Fallback if enabled / timeout policy |
| retrieve (empty) | `no_context` | evidence→answer `skipped` | Return no-context (no fallback) |
| evidence (error) | `error` | context→answer `skipped` | Fallback if enabled |
| evidence (empty) | `no_context` | context→answer `skipped` | Return no-context |
| context (error) | `error` | answer `skipped` | Fallback if enabled |
| context (empty) | `no_context` | answer `skipped` | Return no-context |
| answer (error) | `error` | — | Fallback if enabled |
| answer (clarify) | `clarification` | — | Return clarification |

**Semantic outcomes** (`no_context`, `clarification`, `field_unavailable`) MUST NOT trigger
legacy fallback — they are valid business outcomes, not infrastructure failures.

---

## Validation Rules

- `PipelineModeResolver` MUST NOT return `unified` for projects without indexed content when
  `RAG_PIPELINE_REQUIRE_INDEX=true` (optional future guard).
- Shadow records MUST NOT include `full_prompt` by default (size/PII); opt-in via
  `RAG_PIPELINE_SHADOW_INCLUDE_PROMPT=false` default.
- `UnifiedPipelineResult.stage_traces` MUST contain a `parse` trace for every non-error entry.

---

## Relationships

```text
PipelineExecutionContext 1──1 UnifiedPipelineResult (unified path)
PipelineExecutionContext 1──0..1 ShadowComparisonRecord (shadow path)
UnifiedPipelineResult 1──1 AnswerResult (on success)
ShadowComparisonRecord *──1 project (aggregated nightly)
EvaluationResult (014) *──* ShadowComparisonRecord (via plan_id / question_id correlation)
```
