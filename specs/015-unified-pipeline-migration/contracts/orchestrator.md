# Contract: Pipeline Orchestrator

**Feature**: 015-unified-pipeline-migration | **Version**: 1.0.0

Defines application-layer interfaces for pipeline routing and unified execution. These are
Python Protocol/ABC contracts to be implemented in `services/rag/pipeline/`.

---

## `IPipelineModeResolver`

Resolves effective pipeline mode for a request.

```python
class IPipelineModeResolver(Protocol):
    def resolve(
        self,
        *,
        project_id: int,
        project_config: dict | None,
        settings: PipelineSettings,
    ) -> PipelineMode: ...
```

**Resolution order** (normative):

1. If `project_config.get("pipeline_mode")` is a valid `PipelineMode` → use it
2. Else if `str(project_id)` in `settings.RAG_PIPELINE_CANARY_PROJECT_IDS` → `unified`
3. Else → `settings.RAG_PIPELINE_MODE`

---

## `IPipelineRouter`

Single entry point from `NLPController.answer_rag_question`.

```python
class IPipelineRouter(Protocol):
    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict | None,
        profile: FieldProfile,
    ) -> PipelineAnswerResponse: ...
```

**Behavior by mode**:

| Mode | Normative behavior |
|------|-------------------|
| `legacy` | Invoke `ILegacyPipelineExecutor.execute`; return result |
| `unified` | Invoke `IUnifiedRagOrchestrator.execute`; on failure + fallback enabled → legacy |
| `shadow` | Invoke `IShadowPipelineRunner.execute`; return legacy result; persist comparison |

---

## `ILegacyPipelineExecutor`

Wraps existing `RAGService.answer_question` without modification in Phase 0–3.

```python
class ILegacyPipelineExecutor(Protocol):
    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict | None,
        profile: FieldProfile,
        ctx: PipelineExecutionContext,
    ) -> PipelineAnswerResponse: ...
```

**Guarantee**: Output MUST be bit-for-bit compatible with current production tuple mapping.

---

## `IUnifiedRagOrchestrator`

Executes the SpecKit stage graph.

```python
class IUnifiedRagOrchestrator(Protocol):
    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict | None,
        profile: FieldProfile,
        ctx: PipelineExecutionContext,
    ) -> UnifiedPipelineResult: ...
```

**Stage obligations**:

1. **Parse** — via shared `IQueryParseService` (not duplicated)
2. **Plan** — `IRetrievalPlanner.plan(parse_result, config)`
3. **Retrieve** — `IRetrievalEngine.execute(plan, policy)`
4. **Evidence** — `EvidenceOrchestrator.orchestrate(result, plan, config)`
5. **Context** — `ContextBuilderPipeline.build(pack, config)`
6. **Answer** — `AnswerGenerationPipeline.run(context=..., question=...)`

**Early exits** (no later stages invoked):

- `parse_result.query_plan.needs_clarification`
- `RetrievalPlan.clarification_required` (if planner sets this)
- Zero candidates after retrieve → `no_context`
- Empty evidence pack → `no_context`

---

## `IShadowPipelineRunner`

```python
class IShadowPipelineRunner(Protocol):
    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict | None,
        profile: FieldProfile,
        ctx: PipelineExecutionContext,
    ) -> PipelineAnswerResponse: ...
```

**Normative**:

- MUST run legacy and unified concurrently
- MUST apply timeout to unified branch
- MUST return legacy `PipelineAnswerResponse` to caller
- MUST call `IShadowComparisonStore.save(record)` when persistence enabled

---

## `IQueryParseService`

Shared parser stage extracted from legacy service.

```python
class IQueryParseService(Protocol):
    async def parse(
        self,
        *,
        project: Project,
        query: str,
        profile: FieldProfile,
        session_id: str | None,
    ) -> ParseResult: ...
```

---

## `IResponseAdapter`

```python
class IResponseAdapter(Protocol):
    def from_legacy_tuple(
        self,
        answer: str | None,
        full_prompt: str | None,
        chat_history: list | None,
        needs_clarification: bool,
    ) -> PipelineAnswerResponse: ...

    def from_unified_result(
        self,
        result: UnifiedPipelineResult,
        *,
        original_query: str,
    ) -> PipelineAnswerResponse: ...
```

**Signal mapping** (normative):

| Condition | `ResponseSignal` |
|-----------|------------------|
| `needs_clarification=True` | `RAG_CLARIFICATION_NEEDED` |
| Successful answer | `RAG_ANSWER_SUCCESS` |
| No context / empty answer (orchestrator handles before adapter) | Route layer returns 400 |

---

## `IShadowComparisonStore`

```python
class IShadowComparisonStore(Protocol):
    async def save(self, record: ShadowComparisonRecord) -> None: ...
```

Default implementation: append JSONL to shadow dir.

---

## `IRagPipelineFactory`

Composition-root product.

```python
class IRagPipelineFactory(Protocol):
    def create_router(self) -> IPipelineRouter: ...
```

Built once at startup; stateless aside from injected clients/config.

---

## Error Contract

| Error class | Router behavior |
|-------------|-----------------|
| `UnifiedPipelineTimeout` | Fallback if enabled; else propagate as 400 |
| `UnifiedPipelineError` | Fallback if enabled; log with `request_id` |
| `LegacyPipelineError` | Propagate; shadow: return error, log unified if completed |
| `asyncio.CancelledError` | **Re-raise immediately**; no fallback; no shadow persist |
| Parser disabled (`RAG_SEMANTIC_PARSER_ENABLED=false`) | Same message as legacy; no retrieval |

---

## Cancellation and Timeout Semantics

**Ownership**: `PipelineRouter` / `ShadowRunner` owns the request deadline. Individual stages
MUST NOT start nested `wait_for` with independent timeouts unless ≤ remaining budget.

| Event | Detection | Unified-mode behavior | Shadow-mode behavior |
|-------|-----------|----------------------|----------------------|
| **Deadline exceeded** | `time.perf_counter() >= ctx.deadline_at` or `asyncio.wait_for` timeout | `PipelineOutcome=timeout`; fallback if enabled | Return legacy; unified marked `timed_out` in shadow record |
| **Client disconnect** | `asyncio.CancelledError` raised from FastAPI/Starlette | Re-raise; **no** legacy fallback | Cancel both tasks; re-raise; no shadow persist |
| **Stage exception** | Any other exception in stage | `PipelineOutcome=error`; fallback if enabled | Return legacy; capture unified error in shadow record |

**Stage obligation**: Stage implementations and adapters MUST NOT catch `CancelledError` inside
bare `except Exception`. Use `except Exception` only if `CancelledError` is re-raised.

**Legacy path**: Unchanged — no request-level deadline in v1 (preserves backward compatibility).
Only unified and shadow-unified branches honor `ctx.deadline_at`.

---

## Retry Ownership

Retries are **not** orchestrator concerns. Cross-stage retry is forbidden in v1.

| Layer | Retries? | Scope | Notes |
|-------|----------|-------|-------|
| **PipelineRouter / Orchestrator** | No | — | Single pass per stage; failure → outcome + optional fallback |
| **Core stage pipelines (009–013)** | No | — | Already single-pass by design |
| **Infrastructure adapters** | Optional | Single adapter call | Transient DB/vector errors only; max 2 attempts; idempotent reads |
| **LLM / embedding clients** | Yes (existing) | Provider SDK / factory | Unchanged; owned by `stores/llm` |
| **Celery indexing tasks** | Yes (existing) | Ingestion | Out of scope for answer path |

**Retryable** (adapter-internal only): connection reset, pool timeout, rate-limit 429 with
Retry-After.

**Non-retryable**: validation errors, 4xx client errors, empty results, planner/clarification
outcomes, `CancelledError`, deadline exceeded.

---

## Trace Contract

Every `execute()` MUST emit structured log:

```json
{
  "event": "rag_pipeline_complete",
  "request_id": "...",
  "project_id": 1,
  "mode": "unified",
  "outcome": "success",
  "duration_ms": 1234,
  "plan_id": "rp_...",
  "context_id": "ctx_..."
}
```

Prometheus: see plan.md observability section.

---

## Startup and Readiness

**Scope**: Minimal extension of existing startup — no new health microservice.

### Startup validation (fail-fast)

During `build_rag_pipeline_factory(app)`, before attaching to `app`:

| Check | Required when | On failure |
|-------|---------------|------------|
| `app.vectordb_client` connected | always | Startup abort |
| `app.generation_client` / `app.embedding_client` present | always | Startup abort |
| `app.field_registry` loaded | always | Startup abort (existing) |
| `RetrieverRegistry` has ≥1 retriever for configured strategies | `RAG_PIPELINE_MODE` ∈ `{shadow, unified}` | Startup abort with explicit missing-strategy message |
| `app.rag_pipeline_factory` constructed | `RAG_PIPELINE_MODE` ∈ `{shadow, unified}` | Startup abort |

When `RAG_PIPELINE_MODE=legacy`, factory construction MAY be lazy or skipped; router falls
back to direct `RAGService` if factory absent.

### Readiness (runtime)

Existing health/base route MAY expose optional field:

```json
{ "rag_pipeline": { "mode": "legacy", "factory_ready": true, "pipeline_version": "1.0.0" } }
```

Readiness is **informational** — do not fail liveness when `factory_ready=false` and mode is
`legacy`. When mode is `unified` and factory is not ready, startup should already have failed.

---
