# Research: Retrieval Engine V2

**Feature**: `010-retrieval-engine-v2` | **Date**: 2026-07-14

**Revision note**: This document supersedes the original research.md. Decisions R4, R6,
and R15 have been revised. Decisions R17–R21 are new.

---

## R1 — Input Contract: Schema Version Validation

**Decision**: The Engine validates `RetrievalPlan.metadata.schema_version` at the
start of `RetrievalEnginePipeline.execute()`:

```python
major = int(schema_version.split(".")[0])
if major > EXPECTED_MAJOR:          # EXPECTED_MAJOR = 1
    raise SchemaMismatchError(...)
```

Minor and patch components are ignored — backward-compatible additions in spec 009
do not require Engine changes. The check occurs before query expansion or any retrieval.

---

## R2 — StrategyRouter Design

**Decision**: `StrategyRouter` is a thin lookup class wrapping `RetrieverRegistry`.

```python
class StrategyRouter:
    def route(self, strategy: StrategyType) -> IRetriever:
        retriever = self._registry.get_retriever(strategy)
        if retriever is None:
            raise RetrieverNotFoundError(strategy)
        return retriever
```

No fallback logic in the router — fallback is pipeline logic. When `RetrieverNotFoundError`
is raised, the pipeline logs a WARNING, records a skip trace step with
`skip_reason = "retriever_not_found"`, and continues with remaining strategies.

The `"hybrid"` meta-strategy is never passed to the router (it is expanded to its
components before routing). The router only handles real `IRetriever` strategies.

---

## R3 — Async Execution Model for Multiple Strategy Legs

**Decision**: All strategy legs (the full leg matrix of `strategy × expander_variant`)
are executed via `asyncio.gather(return_exceptions=True)`:

```python
tasks = [
    _execute_leg(retriever, query, context, policy)
    for retriever, query in resolved_legs
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

Each `_execute_leg` coroutine wraps the retriever call with timeout (from
`TimeoutPolicy.per_retriever_ms`) using `asyncio.wait_for`. Exceptions returned by
individual legs are captured as trace errors; they do not cancel other legs.

**Sequential execution**: Retrievers with `sequential_only = True` (e.g., multi-hop
graph traversal where each step depends on the previous result) are isolated from the
parallel batch and executed sequentially after all parallel legs complete. This is an
opt-in per-retriever flag; the default is `sequential_only = False`.

---

## R4 — IRetriever Interface Design (Revised)

**Decision**: `IRetriever` separates the execution query from the planning context:

```python
class IRetriever(ABC):
    retriever_id: str
    supported_strategy: str    # StrategyType
    sequential_only: bool = False
    experimental: bool = False  # True for Graph, SQL

    @abstractmethod
    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]: ...
```

**`RetrievalQuery`** (frozen=True) contains only what changes per leg:
- `query_text: str` — the query string for this leg
- `strategy: StrategyType` — which strategy is being executed
- `expander_variant_id: str` — which expansion variant produced this query

**`RetrievalContext`** (frozen=True) carries planning context that is the same for all
legs in one execution:
- `plan_id: str`
- `filters: tuple[QueryFilter, ...]` — from `RetrievalPlan.filters`
- `constraints: RetrievalConstraints | None` — from `RetrievalPlan.retrieval_constraints`
- `hints: ExecutionHints | None` — from `RetrievalPlan.execution_hints` (advisory)
- `policy: ExecutionPolicy` — execution policy for this run

**Why this separation**: The original design coupled planning state (filters, constraints,
hints, plan_id) to the per-leg execution query, making `RetrievalQuery` effectively a
second `RetrievalPlan`. Separating them:
1. Makes `RetrievalQuery` trivially constructible by the expander (just a query string + metadata).
2. Keeps `RetrievalContext` constant across all legs of one execution — no re-copying.
3. Makes retriever interfaces testable with minimal fixtures.
4. Makes future per-leg query transformations (e.g., rewriting query text for expansion) clean.

**Alternative considered — pass full `RetrievalPlan` to each retriever**: Over-couples
retrievers to the plan schema; every plan evolution requires retriever review; rejected.

---

## R5 — Reciprocal Rank Fusion (RRF) Algorithm

**Decision**: `RRFScoreFuser` implements the standard RRF formula:

```
score(d, k) = Σ_{r ∈ ranked_lists} 1 / (k + rank_r(d))
```

Default `k = 60` (original RRF paper value; configurable via field pack `rrf_k`).
Documents not present in a list contribute 0 for that list (not worst-ranked).

Deduplication: after computing RRF scores for all chunk_ids seen across all lists, the
fuser produces a single list sorted by descending RRF score. Each `chunk_id` appears
exactly once; the merged candidate retains the highest-quality `content_excerpt` and
`source_ref` from contributing legs.

Score normalization: not performed before RRF. RRF is rank-based, not score-based.
Individual retriever `raw_score` values are preserved in `RawCandidate` for debugging.

---

## R6 — IQueryExpander: Future-Proofed Interface Design (Revised)

**Decision**: `IQueryExpander` is redesigned around `ExpansionContext` and `ExpansionResult`
to support future expansion strategies without pipeline changes:

```python
class IQueryExpander(ABC):
    expander_id: str
    expansion_type: str  # "passthrough", "synonym", "ontology", "entity", "llm", ...

    @abstractmethod
    def expand(self, context: ExpansionContext) -> ExpansionResult: ...
```

```python
class ExpansionContext(BaseModel, frozen=True):
    query_text: str
    intent_category: str | None = None
    entities: tuple[str, ...] = ()
    language: str | None = None
    max_variants: int = 3
```

```python
class ExpansionResult(BaseModel, frozen=True):
    variants: tuple[str, ...]       # expanded query texts (min 1)
    expansion_type: str             # identifies which expansion was applied
    metadata: dict[str, Any] = {}  # expander-specific diagnostics
```

The pipeline builds `ExpansionContext` from `RetrievalPlan` fields and calls
`expander.expand(context)`. It then converts each variant text into a `RetrievalQuery`.
The pipeline never knows about expansion internals.

**Why this is future-proof**:
- A synonym expander only needs `query_text` and `language`.
- An ontology expander uses `intent_category` and `entities`.
- An LLM-based expander can use all fields.
- None of these require pipeline changes — they all receive the same `ExpansionContext`.
- `expansion_type` in `ExpansionResult` enables trace recording and observability of which strategy was used.
- `metadata` allows rich expanders to attach diagnostic information without changing the interface.

**Original design problem**: The first design passed the full `RetrievalPlan` to the
expander, coupling expanders to the plan schema. Expanders do not need retrieval
constraints, execution hints, or strategy lists — they only need the query signal.

---

## R7 — Budget Enforcement Design

**Decision**: Two distinct budget checkpoints:

1. **Pre-reranking cap** (`max_candidates`): After fusion, fused list truncated to
   `max_candidates`. Limits reranker input size (rerankers are expensive per-item).

2. **Post-reranking cap** (`max_evidence_units`): After reranking, truncated to
   `max_evidence_units`. This is the final candidate count.

Both caps are applied by `BudgetEnforcer`:

```python
class BudgetEnforcer:
    def apply_candidate_cap(self, candidates, limits) -> list[RawCandidate]: ...
    def apply_evidence_cap(self, candidates, limits) -> list[RetrievedCandidate]: ...
    def check_latency_budget(self, elapsed_ms, budget_ms) -> bool: ...
```

**CancellationPolicy interaction**: When `CancellationPolicy.cancel_on_budget_exceeded = True`
and `max_candidates` is reached before all strategy legs complete, pending legs are
cancelled rather than executed. This prevents wasted retrieval effort.

---

## R8 — Reranker Integration

**Decision**: `IReranker` is a new interface compatible with existing `RerankerInterface`.
Receives `(query_text: str, candidates: list[RawCandidate])`, returns reordered list.

Pipeline sets `score_source = "reranker"` on all candidates returned by a non-passthrough
reranker; `score_source = "fusion"` when passthrough.

**Timeout handling**: The reranker call is wrapped in `asyncio.wait_for` with
`TimeoutPolicy.per_retriever_ms` (or a separate reranker-specific timeout if configured).
If the reranker times out, `partial = True` is set and fusion ordering is used.

---

## R9 — RetrievalResult ID Scheme

**Decision**: `result_id = "rr_" + SHA256(canonical_payload)[:16]` where:

```
canonical_payload = f"{plan_id}|{sorted_strategies}|{fusion_algorithm}|{reranker_id}"
```

Identical plan + configuration → identical `result_id`. Supports idempotent downstream
caching (constitution Principle VI.5).

---

## R10 — Retrieval Tracing Design

**Decision**: `RetrievalTracer` builds `RetrievalTrace` incrementally. Each
`RetrievalStepTrace` is appended after its leg completes (or fails/times out).
The tracer is created fresh per execution; it is NOT a shared stateful object.

`trace_enabled` in `RetrievalEngineConfig` controls verbosity: when `False`, steps
are summarized (strategy, counts, latency only) rather than including full error details.
`total_latency_ms` and `constraint_violations` are always populated regardless.

**New field**: `retry_count: int` in `RetrievalStepTrace` — records how many times
the retriever was retried for this leg. `0` means no retries (first attempt succeeded).

---

## R11 — RetrievedCandidate Score and Ranking

**Decision**: After reranking (or passthrough), candidates receive 1-based `rank`
values by position. `score` and `score_source`:

- `score_source = "reranker"`: score from the reranker model.
- `score_source = "fusion"`: RRF score from the fuser.
- `score_source = "raw"`: raw retriever score (only when single strategy + single
  variant + `PassthroughReranker`).

No normalization at the final output stage — spec 011 receives scores as-is.

---

## R12 — GraphRetriever: Experimental Extension Point

**Decision**: `GraphRetriever` is an **optional built-in experimental retriever**:
- `supported_strategy = "graph"`
- `experimental = True`
- NOT registered in the default `RetrieverRegistry`
- Requires explicit field pack opt-in: `enabled_strategies` must include `"graph"`
- Uses `KnowledgeRepository` (spec 008) for graph traversal; injected via constructor

**Documentation treatment**: `GraphRetriever` is documented as an extension point that
demonstrates the `IRetriever` interface for non-trivial backends. It is NOT a required
production component. The Engine has zero hard dependency on any graph backend.

---

## R13 — SQLRetriever: Experimental Extension Point

**Decision**: `SQLRetriever` is an **optional built-in experimental retriever**:
- `supported_strategy = "sql"`
- `experimental = True`
- NOT registered in the default `RetrieverRegistry`
- Requires explicit field pack opt-in
- Uses parameterized queries via async SQLAlchemy; zero string interpolation of user input
- SQL query templates live in a field-pack-loadable template registry (not hardcoded)

**Documentation treatment**: Same as `GraphRetriever` — demonstrates extensibility for
structured-data retrieval scenarios.

---

## R14 — Forward Compatibility and Schema Versioning

**Decision**: `RetrievalResult.schema_version = "1.0.0"`. Semantic versioning:
- **MAJOR**: field removed, renamed, or type-narrowed on `RetrievalResult` or required sub-models.
- **MINOR**: new optional field added.
- **PATCH**: documentation or validation changes with no model shape change.

Evidence Orchestrator (spec 011) MUST check the major component at startup and reject
results with `major > expected_major`.

---

## R15 — Hybrid as Pipeline Meta-Strategy (Revised, replaces HybridRetriever)

**Original design problem**: `HybridRetriever` was a dedicated `IRetriever`
implementation that internally composed `DenseVectorRetriever` and `SparseRetriever`.
This had two architectural problems:
1. **Violated single responsibility**: the retriever was doing pipeline-level work
   (parallel execution + fusion) inside an `IRetriever` implementation.
2. **Reduced configurability**: the hybrid composition was fixed at construction time;
   changing hybrid components required subclassing or reconfiguration of the retriever,
   not the pipeline.

**Revised decision**: `"hybrid"` is a **meta-strategy resolved by the pipeline**:

1. `RetrievalEngineConfig` has `hybrid_components: list[str]` (default: `["semantic", "keyword"]`).
2. When the pipeline encounters `"hybrid"` in `retrieval_strategies`, it substitutes it
   with `hybrid_components` in-place before building the leg matrix.
3. The leg matrix is then executed identically to any multi-strategy plan.
4. The trace records the actual component legs, not a single `"hybrid"` step.

**Result**: hybrid execution is first-class pipeline behavior. Changing hybrid composition
is a field pack YAML change (`hybrid_components: [semantic, keyword, metadata]`), not a
code change. The `"hybrid"` shorthand still works as a plan strategy type (spec 009
plans are unchanged) — it is resolved transparently.

```python
def _resolve_strategies(self, strategies: list[str]) -> list[str]:
    resolved = []
    for s in strategies:
        if s == "hybrid":
            resolved.extend(self.config.hybrid_components)
        else:
            resolved.append(s)
    return list(dict.fromkeys(resolved))  # preserve order, deduplicate
```

**Rationale**: This change removes an entire class (`HybridRetriever`) while making
hybrid behavior more transparent, configurable, and consistent with the existing
multi-strategy execution path.

---

## R16 — Domain Field Packs: Retrieval Engine Configuration

**Decision**: Three field pack YAML files:

**`src/fields/generic/retrieval_engine.yaml`**:
```yaml
enabled_strategies: [semantic, keyword, metadata, structured, mixed]
hybrid_components: [semantic, keyword]
default_strategy: semantic
fusion_algorithm: rrf
rrf_k: 60
reranker_backend: passthrough
max_expander_variants: 3
trace_enabled: true
partial_results_allowed: true
budget_defaults:
  max_candidates: 50
  max_evidence_units: 10
# experimental retrievers are opt-in:
# enabled_strategies: [..., graph, sql]
```

**`src/fields/legal/retrieval_engine.yaml`**:
```yaml
enabled_strategies: [semantic, keyword, metadata, structured]
hybrid_components: [semantic, keyword]
reranker_backend: cross_encoder
rrf_k: 30
budget_defaults:
  max_candidates: 30
  max_evidence_units: 8
```

**`src/fields/pharmacy/retrieval_engine.yaml`**:
```yaml
enabled_strategies: [semantic, keyword, metadata, structured, hybrid]
hybrid_components: [semantic, keyword, metadata]
reranker_backend: bge_reranker
budget_defaults:
  max_candidates: 40
  max_evidence_units: 10
```

**Key difference from original**: `"hybrid"` is not an `enabled_strategies` entry that
requires a registered retriever — it is handled by the pipeline's meta-strategy resolver.
`hybrid_components` explicitly lists which real retrievers constitute the hybrid execution.

---

## R17 — ExecutionPolicy Design

**Decision**: `ExecutionPolicy` is a first-class, immutable value object passed into
`RetrievalEnginePipeline.execute()`. It is separate from `RetrievalPlan` because:
1. Execution concerns (retry, timeout, cancellation) are operational, not domain-specific.
2. The same plan may be executed with different policies (strict timeout in production,
   no timeout in development).
3. Decoupling avoids polluting the spec 009 `RetrievalPlan` contract with operational fields.

Sub-policies (all frozen=True, all have conservative safe defaults):

```python
class TimeoutPolicy(BaseModel, frozen=True):
    per_retriever_ms: int | None = None    # None = no per-retriever timeout
    total_pipeline_ms: int | None = None   # None = no total timeout

class RetryPolicy(BaseModel, frozen=True):
    max_attempts: int = 1                  # 1 = no retry
    backoff_ms: int = 0                    # 0 = no backoff
    retryable_on: tuple[str, ...] = ()     # error type names; empty = retry all

class CancellationPolicy(BaseModel, frozen=True):
    cancel_on_budget_exceeded: bool = True
    cancel_on_timeout: bool = True

class PartialResultPolicy(BaseModel, frozen=True):
    allow_partial: bool = True
    min_candidates_required: int = 0       # 0 = empty result is OK

class ExecutionPolicy(BaseModel, frozen=True):
    timeout: TimeoutPolicy = TimeoutPolicy()
    retry: RetryPolicy = RetryPolicy()
    cancellation: CancellationPolicy = CancellationPolicy()
    partial_result: PartialResultPolicy = PartialResultPolicy()
```

`ExecutionPolicy()` (default instance) applies conservative safe defaults suitable for
any environment. All timeouts are disabled, retries are disabled, partial results are
allowed, cancellation on budget is enabled.

**Retry mechanics**: The pipeline wraps each leg execution in a retry loop:
```python
for attempt in range(policy.retry.max_attempts):
    try:
        result = await asyncio.wait_for(retriever.retrieve(q, ctx), per_retriever_ms)
        break
    except Exception as e:
        if attempt == max_attempts - 1:
            record_failure(e, retry_count=attempt)
        else:
            await asyncio.sleep(backoff_ms / 1000)
```

**Rationale**: Policy-as-value-object is idiomatic for async Python systems. All
operational concerns are in one place, not scattered across pipeline stages as
hardcoded values.

---

## R18 — StructuredRetriever: Replacement for TableRetriever

**Decision**: `StructuredRetriever` replaces `TableRetriever` as a built-in retriever.

```python
class StructuredRetriever(BaseRetriever):
    retriever_id = "structured"
    supported_strategy = "structured"
    experimental = False
```

The `"structured"` strategy covers:
- Table cells and table rows
- Key-value structured blocks (e.g., drug interaction cards, product spec sheets)
- Form fields and structured forms
- Any document section marked with a structured content type by the chunker (spec 007)

**Motivation for rename**: "table" was too narrow. Document intelligence pipelines
(spec 006) and chunking (spec 007) produce various structured content types beyond
tables. `StructuredRetriever` is semantically aligned with the upstream document model
and is more generic.

**Strategy vocabulary update**: The generic strategy vocabulary moves from `"table"` to
`"structured"`. Spec 009's `StrategyType` vocabulary is open/extensible (not a closed
enum), so this is an additive change. The planner field packs (spec 009) will use
`"structured"` when updated; `"table"` remains a valid string that an operator may
configure but is considered a legacy alias.

**StructuredRetriever behavior**: Uses content-type metadata from spec 007 chunks
(`StructuralElement.element_type`) to filter for structured elements. Returns
`RawCandidate` objects with `content_excerpt` containing serialized structured content
(e.g., table rows as key:value pairs).

---

## R19 — RetrievalQuery vs RetrievalContext Separation

**Decision**: Formal separation of per-leg variation from plan-level context:

| Field | In `RetrievalQuery` | In `RetrievalContext` | Rationale |
|---|---|---|---|
| `query_text` | ✅ | — | Changes per expander variant |
| `strategy` | ✅ | — | Changes per strategy leg |
| `expander_variant_id` | ✅ | — | Changes per variant |
| `plan_id` | — | ✅ | Constant for all legs in one execution |
| `filters` | — | ✅ | From plan, same for all legs |
| `constraints` | — | ✅ | From plan, same for all legs |
| `hints` | — | ✅ | From plan, same for all legs |
| `policy` | — | ✅ | Same policy for all legs |

`RetrievalContext` is built once per `execute()` call and shared across all legs.
`RetrievalQuery` is built once per `(strategy, variant)` pair.

This design minimizes object creation overhead for large leg matrices and makes
retriever implementations simpler to test (small, focused inputs).

---

## R20 — Non-Functional Requirements: Retry, Timeout, Cancellation

**Decision**: All three are governed exclusively by `ExecutionPolicy`. Implementation
mechanics:

- **Timeout**: `asyncio.wait_for(coro, timeout=policy.timeout.per_retriever_ms / 1000)`
  raises `asyncio.TimeoutError`, which the pipeline catches per leg.
- **Retry**: Outer `for attempt in range(max_attempts)` loop in `_execute_leg()` with
  `asyncio.sleep(backoff_ms / 1000)` between attempts.
- **Cancellation**: `asyncio.gather(return_exceptions=True)` tasks can be cancelled
  by calling `task.cancel()` when budget is exceeded or total timeout fires. The
  pipeline gathers pending tasks for cancellation before assembling the final result.
- **Determinism**: Given identical inputs and mock retrievers (all sync), the pipeline
  is deterministic. Async scheduling non-determinism only affects wall-clock timings,
  not the logical result ordering.

---

## Summary of All Decisions

| Decision | Choice | Revised? |
|---|---|---|
| Schema version check | Major component check; `SchemaMismatchError` on major > 1 | — |
| Strategy routing | `StrategyRouter` wraps registry; `RetrieverNotFoundError` on miss → skip + trace | — |
| Async execution | `asyncio.gather(return_exceptions=True)` for all legs | — |
| `IRetriever` interface | `retrieve(query: RetrievalQuery, context: RetrievalContext)`; `experimental` flag | ✅ R4 |
| `RetrievalQuery` | Minimal: `query_text`, `strategy`, `expander_variant_id` only | ✅ R19 |
| `RetrievalContext` | Planning context: `plan_id`, `filters`, `constraints`, `hints`, `policy` | ✅ R19 (new) |
| RRF fusion | Rank-based, `k=60` default, dedup by `chunk_id` | — |
| `IQueryExpander` | `expand(ExpansionContext) -> ExpansionResult`; `expansion_type` on interface | ✅ R6 |
| Budget enforcement | Two checkpoints: `max_candidates` pre-reranker, `max_evidence_units` post-reranker | — |
| Reranker integration | `IReranker` wraps existing `RerankerInterface`; `PassthroughReranker` default | — |
| `result_id` | `"rr_" + SHA256(plan_id|strategies|fusion|reranker)[:16]` | — |
| Tracing | Incremental; `retry_count` added to step trace | ✅ R10 |
| Hybrid execution | Pipeline meta-strategy resolution; NO `HybridRetriever` | ✅ R15 |
| `StructuredRetriever` | Replaces `TableRetriever`; covers tables, key-value, forms, structured blocks | ✅ R18 (new) |
| `ExecutionPolicy` | Four sub-policies (timeout, retry, cancellation, partial); frozen; default is safe | ✅ R17 (new) |
| `GraphRetriever` | Experimental, optional, NOT registered by default | ✅ R12 |
| `SQLRetriever` | Experimental, optional, NOT registered by default | ✅ R13 |
| Domain field packs | `hybrid_components` list in YAML; experimental strategies require opt-in | ✅ R16 |
