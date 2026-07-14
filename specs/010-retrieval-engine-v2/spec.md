# Feature Specification: Retrieval Engine V2

**Feature Branch**: `010-retrieval-engine-v2`

**Created**: 2026-07-14

**Status**: Draft (Revised)

## Architecture Overview

The Retrieval Engine V2 occupies the execution layer immediately downstream of the
Retrieval Planner:

```
User Query
    ↓
Query Analysis
    ↓
Retrieval Planner (spec 009)
    ↓
RetrievalPlan               ← stable input contract from spec 009
    ↓
Retrieval Engine V2         ← this spec
    ↓
RetrievalResult             ← stable output contract for spec 011
    ↓
Evidence Orchestrator (spec 011)
    ↓
Context Builder (spec 012)
    ↓
Answer Generator (spec 013)
```

**Responsibility boundary**:

| Component | Responsibility |
|---|---|
| Retrieval Planner (spec 009) | Decides *what* to retrieve and *under what constraints* |
| **Retrieval Engine V2** | **Translates plan into store operations; expands queries; executes strategy legs; fuses, reranks, and budgets results; enforces execution policies; traces execution** |
| Evidence Orchestrator (spec 011) | Organizes retrieved candidates into coherent evidence sets |

The Engine MUST NOT perform planning (Planner's responsibility) and MUST NOT organize
evidence into structured sets (Evidence Orchestrator's responsibility).

**Engine internal pipeline**:

```
RetrievalPlan + ExecutionPolicy
    ↓
Schema Version Check
    ↓
Query Expander (IQueryExpander)   → ExpansionContext → ExpansionResult
    ↓ N query variants
Hybrid Meta-Strategy Resolver     → "hybrid" expanded to component strategies
    ↓
Parallel Strategy Executor
    ├── StrategyRouter → IRetriever (dense)            ─┐
    ├── StrategyRouter → IRetriever (sparse)            ├─ asyncio.gather
    ├── StrategyRouter → IRetriever (metadata)          ┘
    └── ... one leg per (strategy × variant)
    ↓ N ranked lists of RawCandidates
Score Fuser (IScoreFuser — default: RRF)
    ↓ merged, deduplicated list (≤ max_candidates)
Reranker (IReranker — default: passthrough)
    ↓ reranked candidates
Budget Enforcer (max_evidence_units)
    ↓
Tracer → RetrievalTrace
    ↓
RetrievalResult
```

**Key architectural notes**:

- **`"hybrid"` is a meta-strategy**, not a dedicated retriever. When the plan specifies
  `"hybrid"`, the pipeline resolves it to its configured component strategies (default:
  `["semantic", "keyword"]`) and executes them as parallel legs before fusion. No
  `HybridRetriever` exists; hybrid execution is first-class pipeline behavior.
- **`ExecutionPolicy`** is a first-class input alongside `RetrievalPlan`. It governs
  timeout, retry, cancellation, and partial-result behavior independently of any
  retriever implementation.
- **`RetrievalQuery`** is a minimal execution token — only the information a retriever
  needs to perform one retrieval leg. Planning context travels separately in
  `RetrievalContext`.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Execute Dense Vector Search from Plan (Priority: P1)

A developer passes a `RetrievalPlan` with `retrieval_strategies = ["semantic"]` and
a default `ExecutionPolicy` to the Retrieval Engine. The Engine translates the plan
into a dense vector search, retrieves candidates within the plan's budget, and returns
a `RetrievalResult` containing scored, attributed candidates with a full execution trace.

**Why this priority**: Dense vector (semantic) search is the most common strategy and
the MVP path for all downstream specs. Without a working end-to-end `RetrievalResult`,
specs 011–013 cannot be developed.

**Independent Test**: Can be fully tested with a mock `DenseVectorRetriever`, asserting
that `RetrievalResult` contains candidates with scores, `source_ref` populated when
`citation_required = true`, a non-empty trace, and that the `max_evidence_units` budget
is respected.

**Acceptance Scenarios**:

1. **Given** a plan with `retrieval_strategies = ["semantic"]` and `max_candidates = 20`, **When** the Engine executes, **Then** a `RetrievalResult` is returned with at most 20 candidates each with a non-null score.
2. **Given** a plan with `max_evidence_units = 5`, **When** the Engine returns results, **Then** the final `candidates` list contains at most 5 items.
3. **Given** a plan with `citation_required = true`, **When** the Engine returns candidates, **Then** each candidate has a populated `source_ref` (document_id, chunk_id, location metadata).
4. **Given** any plan, **When** the Engine executes, **Then** `RetrievalResult.trace` contains at least one `RetrievalStepTrace` recording strategy, raw count, and latency_ms.
5. **Given** a plan with empty `retrieval_strategies` (clarification-required), **When** the Engine receives it, **Then** it returns an empty `RetrievalResult` with `partial = False` and no exception raised.

---

### User Story 2 — Multi-Strategy Execution and Hybrid Meta-Strategy (Priority: P2)

A developer passes a `RetrievalPlan` with multiple ordered strategies (e.g.,
`["semantic", "keyword", "metadata"]`) or the special `"hybrid"` meta-strategy.
For multi-strategy plans, the Engine executes each strategy in parallel and fuses
results via RRF. For `"hybrid"`, the Engine automatically resolves it to its
configured component strategies (default: `["semantic", "keyword"]`) and executes
them as parallel legs — no special retriever is needed.

**Why this priority**: Multi-strategy and hybrid retrieval are the primary quality
drivers for complex queries. Fusion across parallel retrieval legs is what separates
production RAG from naive single-strategy search. The hybrid meta-strategy provides a
first-class shorthand without adding retriever complexity.

**Independent Test**: Can be fully tested with deterministic mock retrievers.
For the multi-strategy case: two mock retrievers with overlapping results → fused result
deduplicates correctly, trace records two legs. For the hybrid case: plan with
`retrieval_strategies = ["hybrid"]` → pipeline expands to configured components,
executes both legs, fuses — trace records two strategy legs, not one.

**Acceptance Scenarios**:

1. **Given** `retrieval_strategies = ["semantic", "keyword"]`, **When** the Engine executes, **Then** both strategies run in parallel, results are fused and deduplicated (same `chunk_id` appears once), and the trace records two strategy legs.
2. **Given** `retrieval_strategies = ["hybrid"]`, **When** the Engine executes, **Then** the pipeline resolves `"hybrid"` to its component strategies (e.g., `["semantic", "keyword"]`), executes both as parallel legs, fuses the results, and records the component legs in the trace — not a single `"hybrid"` leg.
3. **Given** fused candidates exceeding `max_candidates`, **When** budget enforcement runs, **Then** only `max_candidates` candidates proceed to reranking.
4. **Given** one strategy returns zero candidates, **When** fusion runs, **Then** the result contains candidates from the other strategies only, with the zero-result step recorded in the trace.
5. **Given** a plan with `retrieval_strategies = ["hybrid"]` and the Engine configured with `hybrid_components: ["semantic", "keyword", "metadata"]`, **When** the Engine executes, **Then** all three component strategies are executed as parallel legs and fused.

---

### User Story 3 — Reranking After Fusion (Priority: P2)

A developer configures the Retrieval Engine with a reranker (cross-encoder or API
reranker). After score fusion, the Engine applies reranking to the pre-budget candidate
list. A no-op `PassthroughReranker` ensures the pipeline works in degraded mode
without a live reranker. Timeout policy governs reranker execution time.

**Why this priority**: Reranking is mandated by the project constitution (Principle VI.2)
for production RAG. The degraded-mode passthrough ensures development velocity is not
blocked.

**Independent Test**: Can be fully tested with a mock reranker that reverses candidate
order, asserting reversed order in the final result and `metadata.reranker_used = true`.

**Acceptance Scenarios**:

1. **Given** a configured reranker returns reordered candidates, **When** the Engine executes, **Then** `RetrievalResult.candidates` reflect reranker ordering and `metadata.reranker_used = true`.
2. **Given** `PassthroughReranker`, **When** the Engine executes, **Then** fusion-score ordering is preserved and `metadata.reranker_used = false` with no exception raised.
3. **Given** the reranker exceeds `TimeoutPolicy.per_retriever_ms`, **When** the Engine detects the breach, **Then** it records a constraint violation in the trace, sets `partial = True` per `PartialResultPolicy`, and returns the fusion-ordered result.

---

### User Story 4 — Query Expansion and Multi-Query Retrieval (Priority: P3)

A developer configures the Engine with a query expander that generates N query variants.
The Engine executes all variants as independent retrieval legs, fuses the results, and
returns a single deduplicated `RetrievalResult`. The expander interface is designed to
support future expansion strategies (synonym, ontology, entity, LLM-based) without
changing the pipeline.

**Why this priority**: Query expansion improves recall for under-specified queries. The
interface is future-proofed so richer expanders slot in without pipeline changes.

**Independent Test**: Can be fully tested with a deterministic mock expander returning
3 variants, asserting the trace records 3 legs and the result contains deduplicated
candidates from all legs.

**Acceptance Scenarios**:

1. **Given** an expander producing 3 variants, **When** the Engine executes, **Then** the trace records 3 retrieval legs and the result is a fused, deduplicated set.
2. **Given** `PassthroughExpander` (1 variant), **When** the Engine executes, **Then** exactly one retrieval leg per strategy is recorded.
3. **Given** a new LLM-based expander registered in `RetrieverRegistry`, **When** it is configured as the active expander, **Then** the pipeline calls it via `IQueryExpander.expand(context: ExpansionContext)` with no pipeline code change.
4. **Given** `max_expander_variants = 3` in config, **When** an expander returns 5 variants, **Then** only 3 variants are used and the excess is discarded.

---

### User Story 5 — Execution Policies and Graceful Degradation (Priority: P3)

An operator configures `ExecutionPolicy` with custom timeout, retry, cancellation, and
partial-result behavior. The Engine respects all policy settings throughout execution.
When individual strategy legs fail, the Engine degrades gracefully by continuing with
remaining strategies.

**Why this priority**: Production systems require predictable, configurable failure
behavior. Hardcoded timeouts and retry logic become maintenance liabilities. First-class
policies make failure behavior explicit, testable, and operator-configurable.

**Independent Test**: Can be fully tested without real backends. A mock retriever that
simulates timeout or failure verifies that policy enforcement produces the expected
`partial`, constraint violations, and retry behavior in the trace.

**Acceptance Scenarios**:

1. **Given** `TimeoutPolicy(per_retriever_ms=100)` and a mock retriever that takes 200 ms, **When** the Engine executes, **Then** the leg is cancelled, the step trace records `skipped=True, skip_reason="timeout"`, and remaining strategies continue.
2. **Given** `RetryPolicy(max_attempts=3)` and a mock retriever that fails twice then succeeds, **When** the Engine executes, **Then** the retriever is called three times and the successful result is used; the step trace records retry count.
3. **Given** `CancellationPolicy(cancel_on_budget_exceeded=True)` and `max_candidates` already reached after the first strategy, **When** the Engine would start the next strategy, **Then** it skips it with `skip_reason="budget_exhausted"`.
4. **Given** `PartialResultPolicy(allow_partial=False, min_candidates_required=5)` and all strategies return zero candidates, **When** execution completes, **Then** the Engine raises `InsufficientCandidatesError` rather than returning an empty result.

---

### User Story 6 — Pluggable Backends and Domain-Agnostic Configuration (Priority: P3)

An operator registers a new retriever via `RetrieverRegistry` and configures it via
field pack YAML. A plan referencing its strategy immediately uses it without Engine core
changes. The Engine ships with optional experimental retrievers (`GraphRetriever`,
`SQLRetriever`) as documented extension points — they are not registered by default and
require explicit opt-in.

**Why this priority**: Extensibility without architecture change is a non-negotiable
property inherited from spec 002 and the constitution.

**Independent Test**: Register a custom `MockNewRetriever(strategy="custom_v1")` →
execute plan with `retrieval_strategies = ["custom_v1"]` → mock results appear in
`RetrievalResult` with zero Engine core file changes.

**Acceptance Scenarios**:

1. **Given** a new `MockNewRetriever` registered under `"custom_v1"`, **When** a plan with that strategy is executed, **Then** mock results appear in `RetrievalResult` with no Engine core file changes.
2. **Given** a field pack that enables only `["semantic", "keyword"]`, **When** a plan with `retrieval_strategies = ["graph"]` arrives, **Then** the Engine records `RetrieverNotFoundError` in the trace and returns available results from other strategies, not a hard failure.
3. **Given** the pharmacy field pack with `hybrid_components: ["semantic", "keyword", "metadata"]`, **When** a `"hybrid"` plan executes, **Then** all three components run as parallel legs.

---

### Edge Cases

- What happens when `retrieval_strategies` is empty (clarification-required plan)? — Engine returns an empty `RetrievalResult` with `partial = False`, trace records a skip with `skip_reason = "empty_strategy_list"`.
- What happens when `"hybrid"` strategy has no `hybrid_components` configured? — Engine falls back to default `["semantic", "keyword"]`; logs a WARNING; records note in trace.
- What happens when a retriever returns zero candidates? — Empty result step recorded in trace; next strategy continues; final result may be empty (not an error).
- What happens when a retriever raises an exception and retry is exhausted? — Failure recorded in step trace with `error` populated; remaining strategies continue; final `partial` flag set per `PartialResultPolicy`.
- What happens when schema version major > 1? — `SchemaMismatchError` raised before any execution; `RetrievalResult` is never partially produced.
- What happens when `latency_budget_ms` is exceeded mid-execution? — Engine cancels pending legs per `CancellationPolicy`, sets `partial = True`, records constraint violation in trace.
- What happens when two strategies return the same `chunk_id`? — Fusion deduplicates; only one `RetrievedCandidate` per `chunk_id` in the final result.
- What happens when `PartialResultPolicy.allow_partial = False` and not enough candidates are found? — Engine raises `InsufficientCandidatesError` instead of returning empty result.
- What happens when a strategy not registered in the registry is encountered? — `RetrieverNotFoundError` recorded in trace; that leg is skipped; engine continues with remaining strategies.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Engine MUST accept a `RetrievalPlan` (spec 009 schema version `1.0.0`) and an `ExecutionPolicy` as its execution inputs.
- **FR-002**: The Engine MUST check `RetrievalPlan.metadata.schema_version` major component at startup. If `major > 1`, raise `SchemaMismatchError` before any retrieval begins.
- **FR-003**: The Engine MUST route each `StrategyType` in `retrieval_strategies` to a registered `IRetriever` via `StrategyRouter`. Unregistered strategies are recorded as skip steps in the trace and do not halt execution.
- **FR-004**: The Engine MUST support pluggable `IRetriever` implementations registered via `RetrieverRegistry`. Built-in required implementations: `DenseVectorRetriever` (strategy: `"semantic"`), `SparseRetriever` (strategy: `"keyword"`), `MetadataRetriever` (strategy: `"metadata"`), `StructuredRetriever` (strategy: `"structured"` — handles tables, key-value blocks, forms, and structured sections). Built-in optional/experimental implementations: `GraphRetriever` (strategy: `"graph"`, experimental), `SQLRetriever` (strategy: `"sql"`, experimental). Experimental retrievers are NOT registered by default and require explicit field pack opt-in.
- **FR-005**: The `"hybrid"` strategy MUST be treated as a meta-strategy by the pipeline. When `"hybrid"` appears in `retrieval_strategies`, the pipeline MUST resolve it to the configured `hybrid_components` list (default: `["semantic", "keyword"]`) and execute each component as a separate parallel retrieval leg. No dedicated `HybridRetriever` exists.
- **FR-006**: The Engine MUST support pluggable `IQueryExpander` implementations. `PassthroughExpander` MUST be the default. The expander interface MUST accept an `ExpansionContext` and return an `ExpansionResult` containing N query text variants. Future expander implementations (synonym, ontology, entity, LLM-based) MUST be addable via `RetrieverRegistry` without pipeline code changes.
- **FR-007**: The Engine MUST support pluggable `IScoreFuser` implementations. `RRFScoreFuser` (Reciprocal Rank Fusion, `k = 60`) MUST be the built-in default. The fuser MUST deduplicate candidates by `chunk_id` and merge scores.
- **FR-008**: The Engine MUST support pluggable `IReranker` implementations. `PassthroughReranker` MUST be the default. Reranking is applied after fusion and before final budget enforcement.
- **FR-009**: The Engine MUST honor all settings in `ExecutionPolicy` during pipeline execution. `ExecutionPolicy` governs: timeout (per-retriever and total pipeline), retry (attempts, backoff), cancellation (on budget exceeded, on timeout), and partial-result behavior (allow partial, minimum candidates required).
- **FR-010**: The Engine MUST enforce `RetrievalLimits.max_candidates` — the maximum number of candidates entering the reranking step after fusion.
- **FR-011**: The Engine MUST enforce `RetrievalLimits.max_evidence_units` — the maximum number of candidates in the final `RetrievalResult.candidates` after reranking.
- **FR-012**: The Engine MUST apply `RetrievalConstraints` during execution: `required_language` as a post-retrieval filter, `freshness_window` as a document-age filter, `latency_budget_ms` as an execution time gate.
- **FR-013**: The Engine MUST produce a `RetrievalTrace` containing a `RetrievalStepTrace` for every strategy leg attempted (including skipped and failed legs). Each step trace MUST record: `strategy`, `expander_variant_id`, `retriever_id`, `raw_count`, `post_filter_count`, `latency_ms`, `retry_count`, `skipped`, `skip_reason`, and `error`.
- **FR-014**: The Engine MUST produce a `RetrievalResult` as its output contract for spec 011. Required fields: `result_id`, `plan_id`, `candidates`, `trace`, `metadata`, `partial`, `schema_version`.
- **FR-015**: Each `RetrievedCandidate` in `RetrievalResult.candidates` MUST include: `chunk_id`, `document_id`, `score`, `score_source`, `source_ref` (when `citation_required = True`), `content_excerpt`, and `rank` (1-based).
- **FR-016**: `IRetriever.retrieve()` MUST accept a `RetrievalQuery` (minimal execution token: `query_text`, `strategy`, `expander_variant_id`) and a `RetrievalContext` (planning context: `plan_id`, `filters`, `constraints`, `hints`, `policy`). These MUST be separate objects. `RetrievalQuery` MUST NOT carry planning-derived fields that belong on `RetrievalContext`.
- **FR-017**: The Engine MUST execute multiple strategy legs in parallel via async execution unless a leg's retriever declares `sequential_only = True` (opt-in for multi-hop strategies).
- **FR-018**: When `RetryPolicy.max_attempts > 1`, the Engine MUST retry a failed retriever leg according to the configured backoff and max attempt count. Retry count MUST be recorded in the step trace.
- **FR-019**: When `TimeoutPolicy.per_retriever_ms` is set, each retriever call MUST be wrapped in an async timeout. A timed-out leg is treated as failed and the policy governs whether to continue or cancel.
- **FR-020**: The Engine MUST be domain-agnostic — no pharmacy, legal, or domain-specific logic in `src/core/retrieval_engine/` core code. All domain customization via field pack YAML.
- **FR-021**: The Engine MUST be configurable via field pack YAML: `enabled_strategies`, `hybrid_components`, `default_strategy`, `fusion_algorithm`, `reranker_backend`, `max_expander_variants`, `trace_enabled`, `partial_results_allowed`.
- **FR-022**: When `PartialResultPolicy.allow_partial = False` and the result contains fewer candidates than `min_candidates_required`, the Engine MUST raise `InsufficientCandidatesError` rather than returning an empty result.

### Key Entities

- **`RetrievalPlan`**: Read-only input contract from spec 009. Never mutated by the Engine.
- **`ExecutionPolicy`** *(frozen=True)*: First-class execution input governing pipeline behavior. Sub-policies: `TimeoutPolicy` (`per_retriever_ms`, `total_pipeline_ms`), `RetryPolicy` (`max_attempts = 1`, `backoff_ms = 0`, `retryable_on`), `CancellationPolicy` (`cancel_on_budget_exceeded`, `cancel_on_timeout`), `PartialResultPolicy` (`allow_partial = True`, `min_candidates_required = 0`). Default `ExecutionPolicy()` applies conservative safe defaults.
- **`RetrievalQuery`** *(frozen=True)*: Minimal execution token for a single retrieval leg. Fields: `query_text: str`, `strategy: StrategyType`, `expander_variant_id: str`. Contains ONLY what a retriever needs to execute one search — no planning context.
- **`RetrievalContext`** *(frozen=True)*: Planning context passed alongside `RetrievalQuery` to every `IRetriever.retrieve()` call. Fields: `plan_id: str`, `filters: tuple[QueryFilter, ...]`, `constraints: RetrievalConstraints | None`, `hints: ExecutionHints | None`, `policy: ExecutionPolicy`. Retrievers MAY use context for filter application, constraint enforcement, or hint-driven optimization.
- **`ExpansionContext`** *(frozen=True)*: Input to `IQueryExpander`. Fields: `query_text: str`, `intent_category: str | None`, `entities: tuple[str, ...]`, `language: str | None`, `max_variants: int`. Carries enough planning signal for rich future expanders (ontology, entity, LLM-based) without coupling them to the full plan.
- **`ExpansionResult`** *(frozen=True)*: Output of `IQueryExpander`. Fields: `variants: tuple[str, ...]` (expanded query texts), `expansion_type: str` (e.g., `"passthrough"`, `"synonym"`, `"llm"`), `metadata: dict[str, Any]`. Pipeline converts variants into `RetrievalQuery` objects.
- **`SourceRef`** *(frozen=True)*: Attribution record. Fields: `document_id`, `chunk_id`, `page_number`, `section_title`, `chunk_index`, `document_title`. Required when `citation_required = True`.
- **`RawCandidate`** *(frozen=True)*: Output from one `IRetriever.retrieve()` call. Fields: `chunk_id`, `document_id`, `raw_score: float`, `retriever_id`, `strategy`, `expander_variant_id`, `content_excerpt`, `source_ref: SourceRef | None`.
- **`RetrievedCandidate`** *(frozen=True)*: Final candidate in `RetrievalResult`. Fields: `chunk_id`, `document_id`, `score: float`, `score_source: Literal["reranker", "fusion", "raw"]`, `source_ref: SourceRef | None`, `content_excerpt`, `rank: int`.
- **`RetrievalResult`** *(frozen=True)*: Output contract for spec 011. Fields: `result_id`, `plan_id`, `candidates`, `trace`, `metadata`, `partial`, `schema_version = "1.0.0"`.
- **`RetrievalTrace`** *(frozen=True)*: Execution audit record. Fields: `plan_id`, `steps: tuple[RetrievalStepTrace, ...]`, `total_latency_ms`, `constraint_violations: tuple[str, ...]`.
- **`RetrievalStepTrace`** *(frozen=True)*: Per-leg trace. Fields: `step_index`, `strategy`, `expander_variant_id`, `retriever_id: str | None`, `raw_count`, `post_filter_count`, `latency_ms`, `retry_count: int`, `skipped: bool`, `skip_reason: str | None`, `error: str | None`.
- **`RetrievalExecutionMetadata`** *(frozen=True)*: Summary metadata. Fields: `result_id`, `plan_id`, `schema_version`, `executed_strategies`, `hybrid_components_used: tuple[str, ...]`, `fusion_algorithm`, `reranker_used`, `expander_used`, `expander_type: str`, `total_latency_ms`.
- **`IRetriever`**: Abstract interface. Async method: `retrieve(query: RetrievalQuery, context: RetrievalContext) -> list[RawCandidate]`. Properties: `retriever_id: str`, `supported_strategy: StrategyType`, `sequential_only: bool = False`, `experimental: bool = False`.
- **`IQueryExpander`**: Abstract interface. Method: `expand(context: ExpansionContext) -> ExpansionResult`. Properties: `expander_id: str`, `expansion_type: str`. Future implementations (synonym, ontology, LLM) implement this interface without pipeline changes.
- **`IScoreFuser`**: Abstract interface. Method: `fuse(ranked_lists: list[list[RawCandidate]]) -> list[RawCandidate]`. Property: `fuser_id: str`.
- **`IReranker`**: Abstract interface. Async method: `rerank(query_text: str, candidates: list[RawCandidate]) -> list[RawCandidate]`. Properties: `reranker_id: str`.
- **`StrategyRouter`**: Maps `StrategyType → IRetriever`. Raises `RetrieverNotFoundError` for unregistered strategies; does not apply fallback (fallback is pipeline logic).
- **`RetrieverRegistry`**: Central registry for `IRetriever`, `IQueryExpander`, `IScoreFuser`, `IReranker`. Builds pipeline via `build_pipeline(config, policy) -> RetrievalEnginePipeline`.
- **`RetrievalEngineConfig`**: Field-pack-loaded configuration. Fields: `enabled_strategies`, `hybrid_components`, `default_strategy`, `fusion_algorithm`, `rrf_k`, `reranker_backend`, `max_expander_variants`, `trace_enabled`, `partial_results_allowed`.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Engine MUST respect Clean Architecture layer boundaries — no planning logic or evidence organization logic inside `src/core/retrieval_engine/`; store implementations injected via registry.
- **NFR-002**: All `IRetriever.retrieve()` and `IReranker.rerank()` implementations MUST be async. Multi-leg execution MUST use `asyncio.gather(return_exceptions=True)`.
- **NFR-003**: All public Engine I/O interfaces MUST be fully type-hinted. Pydantic v2 models (frozen=True) MUST back `RetrievalResult`, `RetrievedCandidate`, `RetrievalTrace`, `ExecutionPolicy`, and all sub-entities.
- **NFR-004**: `RetrievalResult` MUST be a stable public contract for spec 011. Breaking changes require a schema version increment.
- **NFR-005**: Engine MUST be domain-agnostic; all domain customization via field pack YAML.
- **NFR-006**: Engine MUST be independently testable with mock retrievers — no real vector store, graph DB, FTS index, or SQL DB required for unit tests.
- **NFR-007**: Structured logging MUST include `plan_id`, `strategies_executed`, `candidate_count`, `reranker_used`, `total_latency_ms` at the Engine boundary (INFO on success, WARNING on partial result or constraint violation).
- **NFR-008**: Secrets MUST NOT appear in Engine configuration or logs. Retriever implementations MUST receive credentials via injected configuration.
- **NFR-009**: New retriever, fuser, expander, or reranker implementations MUST be registrable via `RetrieverRegistry` without modifying any Engine core source file.
- **NFR-010**: Engine MUST degrade gracefully — unavailable or failed strategy is skipped with a trace entry; remaining strategies continue.
- **NFR-011**: **Retry** — The Engine MUST support per-leg retry governed by `RetryPolicy`. Default `max_attempts = 1` (no retry). Retry count MUST be recorded in `RetrievalStepTrace`. Retry logic MUST NOT be hardcoded in retriever implementations.
- **NFR-012**: **Timeout** — The Engine MUST enforce `TimeoutPolicy.per_retriever_ms` using async timeout wrappers. Timed-out legs are cancelled and treated as failed per `CancellationPolicy`. `TimeoutPolicy.total_pipeline_ms` caps total execution time.
- **NFR-013**: **Graceful Degradation** — The Engine MUST produce a valid `RetrievalResult` even when all strategy legs fail, unless `PartialResultPolicy.allow_partial = False` and `min_candidates_required > 0`. Partial results MUST set `partial = True`.
- **NFR-014**: **Deterministic Execution** — For identical `RetrievalPlan`, `ExecutionPolicy`, and mock retrievers, the Engine MUST produce an identical `RetrievalResult` including `result_id`. Non-determinism from async scheduling is not a requirement violation provided candidate sets and scores are identical.
- **NFR-015**: **Cancellation** — The Engine MUST support cooperative asyncio cancellation. If the outer coroutine is cancelled, the Engine MUST propagate cancellation to all in-flight retriever tasks and clean up without leaking resources.
- **NFR-016**: **Observability** — `RetrievalTrace` MUST be produced for every execution, including partial and failed ones. Prometheus metrics extension points MUST be available for: retrieval latency per strategy, candidate count per leg, fusion input/output sizes, reranker latency.
- **NFR-017**: **Execution Tracing** — Every `RetrievalStepTrace` MUST be appended before the next leg starts; the trace MUST be consistent and complete even if pipeline execution terminates early (timeout, cancellation, budget exhaustion).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of plans with non-empty `retrieval_strategies` produce a `RetrievalResult` with at least one `RetrievalStepTrace` and `partial = False` under normal conditions with default `ExecutionPolicy`.
- **SC-002**: `RetrievalResult.candidates` never exceeds `max_evidence_units`, verified across all tests.
- **SC-003**: Score fusion deduplicates correctly — the same `chunk_id` never appears twice in `RetrievalResult.candidates`, verified by golden tests with overlapping mock results.
- **SC-004**: A new `IRetriever` implementation can be registered and used by a plan with no modification to any file in `src/core/retrieval_engine/`.
- **SC-005**: `PassthroughReranker` produces a valid `RetrievalResult` for any non-empty plan without errors (degraded-mode guarantee).
- **SC-006**: A plan with `retrieval_strategies = ["hybrid"]` produces a trace with N component strategy legs (not one `"hybrid"` leg), where N = `len(hybrid_components)`.
- **SC-007**: `RetrievalResult` is a stable public contract. The Evidence Orchestrator (spec 011) can consume it without changes to this spec's contract. Breaking changes require a schema version increment.
- **SC-008**: Engine handles empty `retrieval_strategies` gracefully, returning empty `RetrievalResult` without exception.
- **SC-009**: Engine orchestration overhead ≤ 50 ms for a single-strategy mock plan with 20 candidates (excluding actual I/O to stores).
- **SC-010**: `RetrievalTrace` contains a `RetrievalStepTrace` for every attempted strategy leg, verified by `len(trace.steps) == expected_step_count` in integration tests.
- **SC-011**: `TimeoutPolicy.per_retriever_ms = 50` cancels a mock retriever that sleeps 200 ms and records `skip_reason = "timeout"` in the step trace.
- **SC-012**: `RetryPolicy.max_attempts = 3` on a mock retriever that fails twice then succeeds results in the successful response in `RetrievalResult` and `retry_count = 2` in the step trace.

---

## Assumptions

- The Engine receives `RetrievalPlan` objects at schema version `"1.0.0"`. Major version > 1 is rejected.
- `RetrievalPlan` is immutable; the Engine MUST NOT mutate or re-plan it.
- `ExecutionPolicy` is provided by the caller (RAG service or integration layer); a default `ExecutionPolicy()` instance is used when none is supplied.
- Actual retriever implementations depend on injected store infrastructure. The Engine core creates no store connections itself.
- `GraphRetriever` and `SQLRetriever` are experimental extension points — they demonstrate the registry model but are NOT required for a production deployment. They are registered only when explicitly configured in the field pack.
- `"hybrid"` resolves to `["semantic", "keyword"]` by default. Operators may override `hybrid_components` in the field pack without Engine code changes.
- The Evidence Orchestrator (spec 011) is the sole direct consumer of `RetrievalResult`.
- `ExecutionHints` from the plan are advisory. Correctness MUST NOT depend on hint presence.
- The reranker infrastructure (`utils/rerank/`, existing `RerankerInterface`) is present. The Engine's `IReranker` wraps it via the registry.
- `PassthroughReranker` and `PassthroughExpander` are production-valid defaults.
- The RRF formula `score(d) = Σ 1/(k + rank(d))` with `k = 60` is the default fusion approach.
- Score normalization before RRF is handled by the `IScoreFuser` implementation, not the Engine core.
- `RetrievalQuery` carries ONLY execution-specific information. Retrievers that need filter or constraint data access it via `RetrievalContext`.
