# Tasks: Retrieval Engine V2

**Input**: Design documents from `specs/010-retrieval-engine-v2/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅

**Revision note**: Tasks revised to reflect (1) hybrid as pipeline meta-strategy (no
`HybridRetriever`), (2) `StructuredRetriever` replacing `TableRetriever`, (3)
`ExecutionPolicy` as first-class models, (4) `RetrievalQuery` / `RetrievalContext`
separation, (5) future-proofed `IQueryExpander` with `ExpansionContext` / `ExpansionResult`,
(6) `GraphRetriever` and `SQLRetriever` as optional/experimental.

**Tests**: Required per constitution (Principle VII). All user stories include test tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the package skeleton so all subsequent tasks have valid import paths.

- [X] T001 Create `src/core/retrieval_engine/` directory tree with `__init__.py` files for all sub-packages: `expansion/`, `fusion/`, `reranking/`, `retrievers/`, `budget/`, `tracing/`
- [X] T002 Create `tests/unit/core/retrieval_engine/__init__.py` (empty marker for pytest discovery)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, policies, interfaces, registry, router, field pack, and test
fixtures that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `src/core/retrieval_engine/errors.py` — define `RetrievalEngineError` (base), `SchemaMismatchError`, `RetrieverNotFoundError`, `FusionError`, `InsufficientCandidatesError`, `RetrievalConstraintViolation`; all extend `RetrievalEngineError`
- [X] T004 Create `src/core/retrieval_engine/policies.py` — all four sub-policies with `frozen=True` and safe defaults: `TimeoutPolicy` (`per_retriever_ms: int | None = None`, `total_pipeline_ms: int | None = None`), `RetryPolicy` (`max_attempts: int = 1`, `backoff_ms: int = 0`, `retryable_on: tuple[str, ...] = ()`), `CancellationPolicy` (`cancel_on_budget_exceeded: bool = True`, `cancel_on_timeout: bool = True`), `PartialResultPolicy` (`allow_partial: bool = True`, `min_candidates_required: int = 0`); `ExecutionPolicy` (frozen=True, composed of all four; default instance = `ExecutionPolicy()`)
- [X] T005 Create `src/core/retrieval_engine/models.py` — open types: `ScoreSource = Literal["reranker", "fusion", "raw"]`, `FusionAlgorithm = Literal["rrf", "passthrough"]`, `SkipReason = Annotated[str, Field(min_length=1)]`; re-export `StrategyType` from `core.retrieval_planner.models`
- [X] T006 Add to `src/core/retrieval_engine/models.py` — `SourceRef` (frozen=True): `document_id`, `chunk_id`, `page_number: int | None`, `section_title: str | None`, `chunk_index: int | None`, `document_title: str | None`; `RetrievalQuery` (frozen=True, minimal): `query_text: str`, `strategy: StrategyType`, `expander_variant_id: str`; `RetrievalContext` (frozen=True): `plan_id: str`, `filters: tuple[QueryFilter, ...]`, `constraints: RetrievalConstraints | None`, `hints: ExecutionHints | None`, `policy: ExecutionPolicy` — import `QueryFilter`, `RetrievalConstraints`, `ExecutionHints` from `core.retrieval_planner.models`
- [X] T007 Add to `src/core/retrieval_engine/models.py` — `ExpansionContext` (frozen=True): `query_text: str`, `intent_category: str | None = None`, `entities: tuple[str, ...] = ()`, `language: str | None = None`, `max_variants: int = 3`; `ExpansionResult` (frozen=True): `variants: tuple[str, ...]` (min_length=1 validator), `expansion_type: str`, `metadata: dict[str, Any] = {}`
- [X] T008 Add to `src/core/retrieval_engine/models.py` — `RawCandidate` (frozen=True): `chunk_id`, `document_id`, `raw_score: float`, `retriever_id`, `strategy`, `expander_variant_id`, `content_excerpt`, `source_ref: SourceRef | None`; `RetrievedCandidate` (frozen=True): `chunk_id`, `document_id`, `score: float`, `score_source: ScoreSource`, `source_ref: SourceRef | None`, `content_excerpt`, `rank: int`
- [X] T009 Add to `src/core/retrieval_engine/models.py` — `RetrievalStepTrace` (frozen=True): `step_index: int`, `strategy: str`, `expander_variant_id: str`, `retriever_id: str | None`, `raw_count: int`, `post_filter_count: int`, `latency_ms: float`, `retry_count: int = 0`, `skipped: bool = False`, `skip_reason: str | None = None`, `error: str | None = None`; `RetrievalTrace` (frozen=True): `plan_id`, `steps: tuple[RetrievalStepTrace, ...]`, `total_latency_ms: float`, `constraint_violations: tuple[str, ...]`
- [X] T010 Add to `src/core/retrieval_engine/models.py` — `RetrievalExecutionMetadata` (frozen=True): `result_id` (SHA256 per research R9), `plan_id`, `schema_version: str = "1.0.0"`, `executed_strategies: tuple[str, ...]`, `hybrid_components_used: tuple[str, ...] = ()`, `fusion_algorithm: FusionAlgorithm`, `reranker_used: bool`, `expander_used: bool`, `expander_type: str`, `total_latency_ms: float`; `RetrievalResult` (frozen=True): `result_id`, `plan_id`, `candidates: tuple[RetrievedCandidate, ...]`, `trace: RetrievalTrace`, `metadata: RetrievalExecutionMetadata`, `partial: bool`, `schema_version: str = "1.0.0"`
- [X] T011 Add to `src/core/retrieval_engine/models.py` — `RetrievalEngineConfig`: `enabled_strategies: list[str]`, `hybrid_components: list[str] = ["semantic", "keyword"]`, `default_strategy: str = "semantic"`, `fusion_algorithm: FusionAlgorithm = "rrf"`, `rrf_k: int = 60`, `reranker_backend: str = "passthrough"`, `max_expander_variants: int = 3`, `trace_enabled: bool = True`, `partial_results_allowed: bool = True`, `budget_defaults: dict` (max_candidates=50, max_evidence_units=10)
- [X] T012 Create `src/core/retrieval_engine/interfaces.py` — define all five ABCs: `IRetrievalEngine` (async `execute(plan, policy) -> RetrievalResult`), `IRetriever` (async `retrieve(query: RetrievalQuery, context: RetrievalContext) -> list[RawCandidate]`; properties: `retriever_id`, `supported_strategy`, `sequential_only=False`, `experimental=False`), `IQueryExpander` (`expand(context: ExpansionContext) -> ExpansionResult`; properties: `expander_id`, `expansion_type`), `IScoreFuser` (`fuse(ranked_lists) -> list[RawCandidate]`; `fuser_id`), `IReranker` (async `rerank(query_text, candidates) -> list[RawCandidate]`; `reranker_id`)
- [X] T013 Create `src/core/retrieval_engine/router.py` — `StrategyRouter`: `route(strategy: str) -> IRetriever` raises `RetrieverNotFoundError` on miss; `"hybrid"` MUST NOT be passed to router (pipeline resolves it before routing); include defensive assertion
- [X] T014 Create `src/core/retrieval_engine/registry.py` — `RetrieverRegistry`: `register_retriever`, `register_expander`, `register_fuser`, `register_reranker`, and corresponding `get_*` lookups; `build_pipeline(config: RetrievalEngineConfig, policy: ExecutionPolicy | None = None) -> RetrievalEnginePipeline`
- [X] T015 [P] Create `src/fields/generic/retrieval_engine.yaml` — generic field pack per research R16: `enabled_strategies: [semantic, keyword, metadata, structured, mixed]`, `hybrid_components: [semantic, keyword]`, `default_strategy: semantic`, `fusion_algorithm: rrf`, `rrf_k: 60`, `reranker_backend: passthrough`, `max_expander_variants: 3`, `trace_enabled: true`, `partial_results_allowed: true`, `budget_defaults.max_candidates: 50`, `budget_defaults.max_evidence_units: 10`
- [X] T016 [P] Create `tests/unit/core/retrieval_engine/conftest.py` — shared fixtures: `mock_retriever(strategy, candidates)` factory; `mock_reranker(reverse=False)` factory; `mock_fuser`; `policy_default()`, `policy_strict_timeout(ms)`, `policy_retry(attempts)`, `policy_no_partial()` builders; `plan_builder(strategies, max_candidates, max_evidence_units, citation_required)` constructing minimal `RetrievalPlan`; six named plan fixtures: `plan_semantic`, `plan_keyword`, `plan_multi_strategy`, `plan_hybrid`, `plan_empty_strategies`, `plan_with_budget`

**Checkpoint**: Foundation ready — all models, policies, interfaces, registry, router, field pack, and test fixtures exist. User story implementation can begin.

---

## Phase 3: User Story 1 — Execute Dense Vector Search from Plan (Priority: P1) 🎯 MVP

**Goal**: A `RetrievalPlan` with `retrieval_strategies = ["semantic"]` and default
`ExecutionPolicy` produces a fully populated, immutable `RetrievalResult`.

**Independent Test**: `pytest tests/unit/core/retrieval_engine/test_engine_pipeline.py -k semantic`

### Tests (write first, verify they fail before implementation)

- [X] T017 [P] [US1] Create `tests/unit/core/retrieval_engine/test_models.py` — verify: `RetrievalResult` raises on mutation (frozen); `result_id` starts `"rr_"`, 19 chars, deterministic; `schema_version == "1.0.0"`; `RetrievedCandidate.rank` is 1-based; `RetrievalQuery` has exactly 3 fields (`query_text`, `strategy`, `expander_variant_id`); `RetrievalContext` carries `policy: ExecutionPolicy`; static import scan of `src/core/retrieval_engine/` (excluding `retrievers/graph.py`, `retrievers/sql.py`) asserts no import of `stores.vectordb`, `stores.llm`, `utils.rerank`, `repositories.`, psycopg2, asyncpg (SC-004)
- [X] T018 [P] [US1] Create `tests/unit/core/retrieval_engine/test_policies.py` — `ExecutionPolicy()` default has `retry.max_attempts=1`, `timeout.per_retriever_ms=None`, `cancellation.cancel_on_budget_exceeded=True`, `partial_result.allow_partial=True`; frozen enforcement; `TimeoutPolicy` / `RetryPolicy` / `CancellationPolicy` / `PartialResultPolicy` field defaults; nested policy composition
- [X] T019 [P] [US1] Create `tests/unit/core/retrieval_engine/test_router.py` — registered retriever routes correctly; unregistered raises `RetrieverNotFoundError`; passing `"hybrid"` to router raises `AssertionError` (defensive guard)
- [X] T020 [P] [US1] Create `tests/unit/core/retrieval_engine/test_budget_enforcer.py` — `apply_candidate_cap` truncates to `max_candidates`; `apply_evidence_cap` truncates to `max_evidence_units`; zero-budget returns empty; latency check returns True when elapsed > budget
- [X] T021 [P] [US1] Create `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — US1 assertions: `plan_semantic` + mock dense retriever → `RetrievalResult.candidates` ≤ `max_evidence_units`; each candidate has score > 0, `score_source == "raw"` or `"fusion"`, `source_ref` populated when `citation_required=True`; `trace.steps` has exactly one entry; `metadata.reranker_used == False`; `partial == False`; `result_id` identical on two invocations; `metadata.hybrid_components_used == ()`

### Implementation

- [X] T022 [P] [US1] Create `src/core/retrieval_engine/retrievers/base.py` — `BaseRetriever(IRetriever, ABC)`: `retriever_id`, `supported_strategy`, `sequential_only=False`, `experimental=False`; protected `_log_retrieve_start(query, context)` and `_log_retrieve_end(query, count, latency_ms)` helpers
- [X] T023 [P] [US1] Create `src/core/retrieval_engine/retrievers/dense.py` — `DenseVectorRetriever(BaseRetriever)`: `retriever_id="dense_vector"`, `supported_strategy="semantic"`; constructor accepts injected vector store interface; `async retrieve(query, context)`: calls vector store with `query.query_text` and `context.filters`; maps results to `RawCandidate` with `source_ref` populated
- [X] T024 [P] [US1] Create `src/core/retrieval_engine/budget/enforcer.py` — `BudgetEnforcer`: `apply_candidate_cap(candidates, limits) -> list[RawCandidate]`; `apply_evidence_cap(candidates, limits) -> list[RetrievedCandidate]`; `check_latency_budget(elapsed_ms, budget_ms) -> bool`
- [X] T025 [P] [US1] Create `src/core/retrieval_engine/tracing/tracer.py` — `RetrievalTracer`: `append_step(step: RetrievalStepTrace) -> None`; `record_violation(message: str) -> None`; `build_trace(plan_id, total_latency_ms) -> RetrievalTrace`; mutable accumulator, not frozen during construction
- [X] T026 [P] [US1] Create `src/core/retrieval_engine/fusion/rrf.py` — `RRFScoreFuser(IScoreFuser)`: `fuser_id="rrf"`, `expansion_type`-agnostic; `fuse(ranked_lists)`: compute `score = Σ 1/(k + rank)` per chunk_id; deduplicate; sort descending; configurable `k` (default 60)
- [X] T027 [US1] Create `src/core/retrieval_engine/pipeline.py` — `RetrievalEnginePipeline(IRetrievalEngine)`: constructor injects `expander`, `router`, `fuser`, `reranker`, `budget_enforcer`, `tracer_factory`, `config`; `async execute(plan: RetrievalPlan, policy: ExecutionPolicy | None = None) -> RetrievalResult`: (1) schema version check; (2) build `RetrievalContext`; (3) call `expander.expand(ExpansionContext)` → variants; (4) resolve `"hybrid"` meta-strategy via `_resolve_strategies()`; (5) build leg matrix; (6) `asyncio.gather` all legs via `_execute_leg()` (with timeout + retry per policy); (7) fuse; (8) `apply_candidate_cap`; (9) rerank; (10) `apply_evidence_cap`; (11) assign 1-based ranks; (12) assemble trace; (13) check `PartialResultPolicy`; (14) return frozen `RetrievalResult`

**Checkpoint**: US1 complete — single-strategy plan produces valid `RetrievalResult`.

---

## Phase 4: User Story 2 — Multi-Strategy and Hybrid Meta-Strategy (Priority: P2)

**Goal**: Multi-strategy plans execute in parallel and fuse correctly. `"hybrid"` is
resolved to component strategies by the pipeline — no dedicated retriever needed.

**Independent Test**: `pytest tests/unit/core/retrieval_engine/test_engine_pipeline.py -k multi`

### Tests (write first)

- [X] T028 [P] [US2] Create `tests/unit/core/retrieval_engine/test_rrf_fuser.py` — two overlapping lists produce correct combined RRF scores (manually verified); single-list input returned unchanged; empty list returns empty; same chunk_id never appears twice in output; ranking order is descending RRF score
- [X] T029 [P] [US2] Create `tests/unit/core/retrieval_engine/test_sparse_retriever.py` — `SparseRetriever` with mock FTS; `retriever_id == "sparse_fts"`; `supported_strategy == "keyword"`; `context.filters` passed to FTS mock
- [X] T030 [P] [US2] Create `tests/unit/core/retrieval_engine/test_metadata_retriever.py` — `MetadataRetriever` with mock metadata store; `context.filters` applied; correct `RawCandidate` output
- [X] T031 [P] [US2] Update `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — add US2 assertions: `plan_multi_strategy` (semantic+keyword) → no duplicate `chunk_id`s in result; `len(trace.steps) == 2`; `metadata.fusion_algorithm == "rrf"`; `plan_hybrid` → pipeline resolves to component strategies; `len(trace.steps) == len(hybrid_components)`; `metadata.hybrid_components_used` reflects resolved components; `"hybrid"` does NOT appear as a `trace.step.strategy` value

### Implementation

- [X] T032 [P] [US2] Create `src/core/retrieval_engine/retrievers/sparse.py` — `SparseRetriever(BaseRetriever)`: `retriever_id="sparse_fts"`, `supported_strategy="keyword"`; constructor accepts injected FTS store interface; `async retrieve(query, context)`: applies `context.filters`; returns `RawCandidate` list
- [X] T033 [P] [US2] Create `src/core/retrieval_engine/retrievers/metadata.py` — `MetadataRetriever(BaseRetriever)`: `retriever_id="metadata_filter"`, `supported_strategy="metadata"`; applies `context.filters` as metadata predicates; returns `RawCandidate` list
- [X] T034 [US2] Update `src/core/retrieval_engine/pipeline.py` — implement `_resolve_strategies(strategies: list[str]) -> list[str]`: when `"hybrid"` in strategies, substitute with `config.hybrid_components`; deduplicate while preserving order (`dict.fromkeys`); record resolved components in `metadata.hybrid_components_used`; `"hybrid"` MUST NOT be passed to `StrategyRouter`

**Checkpoint**: US2 complete — multi-strategy and hybrid resolution work. Test `pytest tests/unit/core/retrieval_engine/ -k "rrf or sparse or metadata or pipeline_multi"`.

---

## Phase 5: User Story 3 — Reranking After Fusion (Priority: P2)

**Goal**: Configured reranker reorders candidates after fusion; passthrough preserves
fusion order; `TimeoutPolicy` cancels slow reranker.

**Independent Test**: `pytest tests/unit/core/retrieval_engine/test_engine_pipeline.py -k rerank`

### Tests (write first)

- [X] T035 [P] [US3] Update `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — add US3 assertions: mock reversing reranker → result candidates in reversed order vs fusion output; `metadata.reranker_used == True`; `score_source == "reranker"` on all final candidates; `PassthroughReranker` → fusion order preserved, `metadata.reranker_used == False`; `TimeoutPolicy(per_retriever_ms=1)` + slow mock reranker → `partial == True`, constraint violation in trace, fusion ordering used

### Implementation

- [X] T036 [P] [US3] Create `src/core/retrieval_engine/reranking/passthrough.py` — `PassthroughReranker(IReranker)`: `reranker_id="passthrough"`; `async rerank(query_text, candidates) -> list[RawCandidate]`: returns `candidates` unchanged
- [X] T037 [US3] Update `src/core/retrieval_engine/pipeline.py` — add post-fusion reranking step with `asyncio.wait_for(reranker.rerank(...), timeout)` wrapping; on timeout: set `partial=True`, record violation, use fusion-ordered candidates; set `metadata.reranker_used = (reranker.reranker_id != "passthrough")`; set `score_source = "reranker"` or `"fusion"` accordingly

**Checkpoint**: US3 complete — reranking with timeout support works.

---

## Phase 6: User Story 4 — Query Expansion with Future-Proof Interface (Priority: P3)

**Goal**: `PassthroughExpander` works for single-variant default. `IQueryExpander`
accepts `ExpansionContext` / returns `ExpansionResult` — future expanders slot in
without pipeline changes.

**Independent Test**: `pytest tests/unit/core/retrieval_engine/test_query_expander.py`

### Tests (write first)

- [X] T038 [P] [US4] Create `tests/unit/core/retrieval_engine/test_query_expander.py` — `PassthroughExpander.expand(ctx)` returns `ExpansionResult` with `variants = (ctx.query_text,)`, `expansion_type == "passthrough"`, `metadata == {}`; `len(variants) == 1`; mock 3-variant expander returns `ExpansionResult(variants=("v0","v1","v2"), expansion_type="mock")`; `max_expander_variants` cap enforced in pipeline (5-variant expander capped at 3)
- [X] T039 [US4] Update `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — add US4 assertions: N=3 expander + 1 strategy → `len(trace.steps) == 3`; no duplicate `chunk_id`s across all legs; `metadata.expander_used == True`; `metadata.expander_type == "mock"`; passthrough → `metadata.expander_used == False`, `len(trace.steps) == 1` per strategy; new `LLMBasedExpander` (inline in test, implements `IQueryExpander`) registered in registry → pipeline calls it via `expand(ExpansionContext)` with no pipeline code change (SC-004 pattern)

### Implementation

- [X] T040 [P] [US4] Create `src/core/retrieval_engine/expansion/passthrough.py` — `PassthroughExpander(IQueryExpander)`: `expander_id="passthrough"`, `expansion_type="passthrough"`; `expand(context: ExpansionContext) -> ExpansionResult`: returns `ExpansionResult(variants=(context.query_text,), expansion_type="passthrough")`
- [X] T041 [US4] Update `src/core/retrieval_engine/pipeline.py` — finalize expansion step: (1) build `ExpansionContext` from plan (`query_text=plan.canonical_query`, `intent_category=plan.intent.category`, `entities=tuple(e.canonical_form for e in plan.entities)`, `language=context.constraints.required_language if context.constraints else None`, `max_variants=config.max_expander_variants`); (2) call `expander.expand(expansion_ctx)` → `ExpansionResult`; (3) apply `max_expander_variants` cap; (4) build `RetrievalQuery` per variant per strategy; (5) set `metadata.expander_used = (expander.expander_id != "passthrough")`; (6) set `metadata.expander_type = expander.expansion_type`

**Checkpoint**: US4 complete — expansion pipeline works with future-proof interface.

---

## Phase 7: User Story 5 — Execution Policies (Priority: P3)

**Goal**: `TimeoutPolicy`, `RetryPolicy`, `CancellationPolicy`, and `PartialResultPolicy`
are all honored by the pipeline. Policies are configurable; no timeout/retry is hardcoded.

**Independent Test**: `pytest tests/unit/core/retrieval_engine/test_engine_pipeline.py -k policy`

### Tests (write first)

- [X] T042 [P] [US5] Update `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — add US5 assertions: `TimeoutPolicy(per_retriever_ms=5)` + mock retriever sleeping 100 ms → step trace has `skipped=True, skip_reason="timeout"`, remaining strategies continue; `RetryPolicy(max_attempts=3)` + mock failing twice then succeeding → `retry_count == 2` in step trace, result contains successful candidates; `CancellationPolicy(cancel_on_budget_exceeded=True)` + budget reached after leg 1 → leg 2 never executes, step 2 trace has `skipped=True, skip_reason="budget_exhausted"`; `PartialResultPolicy(allow_partial=False, min_candidates_required=5)` + all retrievers return empty → `InsufficientCandidatesError` raised

### Implementation

- [X] T043 [US5] Update `src/core/retrieval_engine/pipeline.py` — implement `_execute_leg()` helper: full retry loop respecting `RetryPolicy`; `asyncio.wait_for` wrapping per `TimeoutPolicy.per_retriever_ms`; exception capture into step trace `error` field; `retry_count` incremented on each retry; cancellation check after each leg completes (per `CancellationPolicy.cancel_on_budget_exceeded`); update `execute()` to check `PartialResultPolicy` before returning

**Checkpoint**: US5 complete — all execution policies honored. Test `pytest tests/unit/core/retrieval_engine/ -k "policy or pipeline_policy"`.

---

## Phase 8: User Story 6 — Pluggable Backends and Domain-Agnostic Configuration (Priority: P3)

**Goal**: Custom retrievers register and work immediately. Experimental retrievers
(`GraphRetriever`, `SQLRetriever`) demonstrate extensibility but are opt-in only.
Domain field packs change behavior without code changes.

**Independent Test**: Register `MockCustomRetriever(strategy="custom_v1")` → execute
plan with that strategy → mock called, result valid, zero Engine core files changed.

### Tests (write first)

- [X] T044 [P] [US6] Create `tests/unit/core/retrieval_engine/test_structured_retriever.py` — `StructuredRetriever` with mock structured store; `supported_strategy == "structured"`; `experimental == False`; handles structured content metadata from `context.hints.allow_table_search`
- [X] T045 [P] [US6] Update `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — add US6 assertions: `MockCustomRetriever(strategy="custom_v1")` registered → plan with `["custom_v1"]` → result contains mock candidates (SC-004); unregistered strategy → step trace `skipped=True, skip_reason="retriever_not_found"`; pharmacy field pack with `hybrid_components: [semantic, keyword, metadata]` → `"hybrid"` plan produces 3-leg trace; `GraphRetriever` not in default registry → plan with `["graph"]` treated as unregistered strategy

### Implementation

- [X] T046 [P] [US6] Create `src/core/retrieval_engine/retrievers/structured.py` — `StructuredRetriever(BaseRetriever)`: `retriever_id="structured"`, `supported_strategy="structured"`, `experimental=False`; constructor accepts structured-content store interface; `async retrieve(query, context)`: filters by structured content types from `context.hints.allow_table_search` or `context.hints.preferred_section_kinds`; returns `RawCandidate` list with structured content excerpts
- [X] T047 [P] [US6] Create `src/core/retrieval_engine/retrievers/graph.py` — `GraphRetriever(BaseRetriever)`: `retriever_id="graph_traversal"`, `supported_strategy="graph"`, `experimental=True`; constructor accepts `KnowledgeRepository` (injected); `async retrieve(query, context)`: entity-seeded graph traversal via `KnowledgeRepository`; documented clearly as **experimental extension point** in module docstring
- [X] T048 [P] [US6] Create `src/core/retrieval_engine/retrievers/sql.py` — `SQLRetriever(BaseRetriever)`: `retriever_id="sql_retriever"`, `supported_strategy="sql"`, `experimental=True`; parameterized queries only (NO string interpolation); template registry injected; documented clearly as **experimental extension point** in module docstring
- [X] T049 [P] [US6] Create `src/fields/legal/retrieval_engine.yaml` — legal overrides: `enabled_strategies: [semantic, keyword, metadata, structured]`, `hybrid_components: [semantic, keyword]`, `reranker_backend: cross_encoder`, `rrf_k: 30`, `budget_defaults.max_candidates: 30`, `budget_defaults.max_evidence_units: 8`
- [X] T050 [P] [US6] Create `src/fields/pharmacy/retrieval_engine.yaml` — pharmacy overrides: `enabled_strategies: [semantic, keyword, metadata, structured, hybrid]`, `hybrid_components: [semantic, keyword, metadata]`, `reranker_backend: bge_reranker`, `budget_defaults.max_candidates: 40`, `budget_defaults.max_evidence_units: 10`
- [X] T051 [US6] Update `src/core/retrieval_engine/registry.py` — register all default (non-experimental) implementations: `DenseVectorRetriever`, `SparseRetriever`, `MetadataRetriever`, `StructuredRetriever`, `PassthroughExpander`, `RRFScoreFuser`, `PassthroughReranker`; do NOT register `GraphRetriever` or `SQLRetriever` by default; document that experimental retrievers require explicit registration in `build_pipeline()` caller

**Checkpoint**: US6 complete — all pluggable backends and domain configs work.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration test suite, observability, static validation, and final e2e check.

- [X] T052 [P] Create `tests/integration/test_retrieval_engine_e2e.py` — 14+ golden plan fixtures with mock retriever pool: `factual_semantic`, `keyword_only`, `hybrid_resolved`, `multi_strategy_2`, `multi_strategy_3`, `structured_plan`, `multi_query_expansion`, `empty_strategies`, `budget_cap`, `timeout_policy`, `retry_policy`, `partial_allowed`, `partial_forbidden`, `custom_retriever`; each asserts: `RetrievalResult` shape; `len(trace.steps) == expected`; `len(candidates) <= max_evidence_units`; no duplicate `chunk_id`s; `schema_version == "1.0.0"`; `result_id` stable; for hybrid: no `"hybrid"` in `trace.steps[*].strategy`, `metadata.hybrid_components_used` non-empty
- [X] T053 [P] Add structured logging to `src/core/retrieval_engine/pipeline.py` — INFO on successful execution: `plan_id`, `strategies_executed`, `hybrid_components_used`, `candidate_count`, `reranker_used`, `expander_used`, `total_latency_ms`; WARNING on `partial=True`; WARNING per `RetrieverNotFoundError` skip; ERROR on `SchemaMismatchError`; DEBUG per step (when `trace_enabled=True`)
- [X] T054 [P] Add no-infra-imports assertion to `tests/unit/core/retrieval_engine/test_models.py` — walk `src/core/retrieval_engine/` excluding `retrievers/graph.py` and `retrievers/sql.py`; assert no import of `stores.vectordb`, `stores.llm`, `utils.rerank`, `repositories.`, psycopg2, asyncpg (SC-004)
- [X] T055 [P] Add SC-004 extensibility test to `tests/unit/core/retrieval_engine/test_engine_pipeline.py` — define `MockNewStrategyRetriever(strategy="new_strategy_v2")` inline in test; register via `RetrieverRegistry`; build pipeline; execute plan with `retrieval_strategies=["new_strategy_v2"]`; assert mock called, result is valid — confirm zero `src/core/retrieval_engine/` files were modified by this test
- [X] T056 [P] Run `pytest tests/unit/core/retrieval_engine/ -v` — all unit tests pass; run `pytest tests/integration/test_retrieval_engine_e2e.py -v` — all golden plans produce valid `RetrievalResult`; verify SC-002 (budget), SC-003 (dedup), SC-006 (hybrid expansion), SC-008 (empty strategies), SC-010 (trace completeness), SC-011 (timeout policy), SC-012 (retry policy)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundation)**: Depends on Phase 1 — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — independent of US2–US6
- **US2 (Phase 4)**: Depends on Phase 2 + US1 pipeline (T027) — start after T027
- **US3 (Phase 5)**: Depends on US1 pipeline (T027) — can run in parallel with US2
- **US4 (Phase 6)**: Depends on US1 pipeline (T027) — can run in parallel with US2 and US3
- **US5 (Phase 7)**: Depends on US1 pipeline (T027) — can run in parallel with US2/US3/US4
- **US6 (Phase 8)**: Retrievers (T046–T048) require only interfaces.py; registry (T051) requires all retrievers complete
- **Polish (Phase 9)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Core MVP — all other stories depend on US1 pipeline
- **US2 (P2)**: Hybrid meta-strategy resolver lives in pipeline.py; start after T027
- **US3 (P2)**: Post-fusion reranking update to pipeline.py; start after T027; parallel with US2
- **US4 (P3)**: Expansion step in pipeline.py; start after T027; parallel with US2 and US3
- **US5 (P3)**: Policy enforcement in `_execute_leg()`; start after T027; parallel with US2/US3/US4
- **US6 (P3)**: Retrievers independent of each other; registry wires them all

### Parallel Opportunities

| Group | Tasks |
|---|---|
| Foundation policies + models (sequential; same files or dependent) | T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 |
| Foundation support files (different files) | T012 [P], T013 [P], T014 [P], T015 [P], T016 [P] |
| US1 tests (different files) | T017 [P], T018 [P], T019 [P], T020 [P], T021 [P] |
| US1 implementations (different files) | T022 [P], T023 [P], T024 [P], T025 [P], T026 [P] |
| US2/US3/US4/US5 test updates (same file) | T031, T035, T039, T042 — sequential edits to test_engine_pipeline.py |
| US2 implementations (different files) | T032 [P], T033 [P] |
| US6 retrievers (different files) | T046 [P], T047 [P], T048 [P], T049 [P], T050 [P] |
| Polish (different files) | T052 [P], T053 [P], T054 [P], T055 [P], T056 [P] |

---

## Parallel Example: User Story 1

```bash
# After Phase 2 complete, launch US1 test stubs in parallel:
T017: test_models.py
T018: test_policies.py
T019: test_router.py
T020: test_budget_enforcer.py
T021: test_engine_pipeline.py (US1 stubs)

# Then US1 implementations in parallel:
T022: retrievers/base.py
T023: retrievers/dense.py
T024: budget/enforcer.py
T025: tracing/tracer.py
T026: fusion/rrf.py

# Then sequential pipeline wiring:
T027: pipeline.py (depends on T022–T026)
```

---

## Implementation Strategy

### MVP First

1. Phase 1: Setup (T001–T002)
2. Phase 2: Foundation (T003–T016) — CRITICAL
3. Phase 3: US1 (T017–T027) — **MVP: single-strategy retrieval working**
4. **STOP and VALIDATE**: `pytest tests/unit/core/retrieval_engine/ -k "models or policies or router or budget or pipeline"`
5. Evidence Orchestrator (spec 011) can start consuming `RetrievalResult` from here

### Incremental Delivery

1. US1 → semantic single-strategy (**MVP**)
2. US2 → multi-strategy + hybrid meta-resolution (**constitution VI.1 compliance**)
3. US3 → reranking (**constitution VI.2 compliance**)
4. US4 → query expansion (**recall improvement**)
5. US5 → execution policies (**production reliability**)
6. US6 → structured retriever + experimental backends (**extensibility**)
7. Polish → golden suite, observability, static analysis

### Parallel Team Strategy

With two developers after Phase 2 + US1:
- **Developer A**: US2 (T028–T034) → US4 (T038–T041) → US6 retrievers (T046–T050)
- **Developer B**: US3 (T035–T037) → US5 (T042–T043) → US6 registry (T051)
- Polish (T052–T056) together

---

## Notes

- `[P]` tasks write to different files — safe to parallelize within the same phase
- Models (T003–T011) are sequential — each adds to the same file
- `"hybrid"` MUST NEVER be passed to `StrategyRouter` — the pipeline resolves it first
- `GraphRetriever` and `SQLRetriever` are experimental: `experimental=True`, not registered by default, require explicit opt-in
- `RetrievalQuery` has exactly 3 fields — if you find yourself adding a 4th, it belongs in `RetrievalContext`
- `ExecutionPolicy` defaults (`max_attempts=1`, `timeout=None`) mean "no retry, no timeout" — safe for any environment
- `IQueryExpander.expand()` takes `ExpansionContext`, not `RetrievalPlan` — decouple expanders from plan schema
- `asyncio.gather(return_exceptions=True)` is mandatory — individual leg failures MUST NOT cancel other legs
- SC-004 extensibility test (T055) must pass with zero modifications to any `src/core/retrieval_engine/` file
- Retry loop in `_execute_leg()` uses `asyncio.sleep(backoff_ms / 1000)` — ensure `max_attempts=1` path has zero sleep overhead
