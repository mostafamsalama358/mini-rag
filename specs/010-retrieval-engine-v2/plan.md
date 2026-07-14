# Implementation Plan: Retrieval Engine V2

**Branch**: `010-retrieval-engine-v2` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-retrieval-engine-v2/spec.md`

**Revision note**: Revised to reflect (1) hybrid as pipeline meta-strategy instead of
a dedicated retriever, (2) `StructuredRetriever` replacing `TableRetriever`,
(3) `ExecutionPolicy` as first-class input, (4) `RetrievalQuery` / `RetrievalContext`
separation, (5) future-proofed `IQueryExpander`, (6) Graph/SQL as optional experimental,
and (7) explicit NFRs for retry, timeout, cancellation, and determinism.

---

## Summary

Introduce **Retrieval Engine V2** — an async, pluggable pipeline that receives an
immutable `RetrievalPlan` (spec 009) and an `ExecutionPolicy`, executes retrieval
strategy legs in parallel, fuses results via RRF, applies optional reranking, enforces
candidate and evidence budgets, and returns a `RetrievalResult` as the stable contract
for the Evidence Orchestrator (spec 011).

**Key architectural points**:

- **No `HybridRetriever`**. The `"hybrid"` strategy is a pipeline meta-strategy resolved
  to configurable `hybrid_components` (default: `["semantic", "keyword"]`). Hybrid
  execution is transparent first-class pipeline behavior.
- **`StructuredRetriever`** covers tables, key-value structures, forms, and structured
  blocks — a generalization over the narrower `TableRetriever`.
- **`ExecutionPolicy`** (timeout, retry, cancellation, partial-result) is a first-class
  input to `execute()`, not hardcoded engine behavior. Default policy is safe for any
  environment.
- **`RetrievalQuery`** is a minimal execution token (query text + strategy + variant id).
  Planning context (filters, constraints, hints) travels in `RetrievalContext` — a
  constant per-execution object shared across all legs.
- **`IQueryExpander`** accepts `ExpansionContext` and returns `ExpansionResult`, enabling
  future synonym/ontology/entity/LLM-based expanders without pipeline changes.
- **`GraphRetriever`** and **`SQLRetriever`** are optional experimental extension points,
  not registered by default, demonstrating the `IRetriever` interface for advanced backends.

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: Pydantic v2 (models + validation); `RetrievalPlan` from
`src/core/retrieval_planner/models.py` (spec 009); field pack YAML via
`core.field_resolution` (spec 002); existing `RerankerInterface` from `utils/rerank/`;
`KnowledgeRepository` from `src/repositories/` (spec 008, for experimental `GraphRetriever`);
`stores/vectordb/` (for `DenseVectorRetriever`); PostgreSQL / SQLAlchemy 2.x async
(for `SparseRetriever` FTS and experimental `SQLRetriever`)

**Storage access**: Retriever implementations access stores. Engine core
(`src/core/retrieval_engine/`) accesses NO stores directly. All store access is
injected via `RetrieverRegistry`.

**Testing**: pytest + pytest-asyncio; `tests/unit/core/retrieval_engine/` (per-component
unit tests with mock retrievers) + `tests/integration/test_retrieval_engine_e2e.py`

**Target Platform**: Linux server, Docker (same as existing platform)

**Performance Goals**: Engine orchestration overhead ≤ 50 ms for a single-strategy mock
plan (SC-009); actual retrieval latency is store-dependent

**Constraints**:
- Engine core MUST NOT import from `stores/`, `utils/rerank/`, or `repositories/`
- `RetrievalResult` immutable once produced — `ConfigDict(frozen=True)`
- `RetrievalPlan` read-only — MUST NOT be mutated
- `"hybrid"` resolved by pipeline before routing — never passed to `StrategyRouter`
- Async throughout — `asyncio.gather(return_exceptions=True)` for parallel legs
- `ExecutionPolicy` governs all timeout, retry, cancellation — no hardcoded values

---

## Constitution Check

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|---|---|---|
| G1 Clean Architecture | Engine core in `src/core/retrieval_engine/`; all store/infra imports injected via registry; no `stores/`, `utils/rerank/`, `repositories/` in core | ✅ |
| G2 Feature-First | All Engine code co-located in `src/core/retrieval_engine/`; tests in `tests/unit/core/retrieval_engine/` | ✅ |
| G3 SOLID / Plugins | Five pluggable interfaces (`IRetriever`, `IQueryExpander`, `IScoreFuser`, `IReranker`, `IRetrievalEngine`); `RetrieverRegistry` wires implementations; `ExecutionPolicy` open to extension; Open/Closed for all backends | ✅ |
| G4 Async + Types | All retriever and reranker calls async; `asyncio.gather` for parallel legs; async timeouts via `asyncio.wait_for`; Pydantic v2 throughout; all public APIs type-hinted | ✅ |
| G5 RAG Pipeline | Multi-strategy hybrid execution satisfies Principle VI.1; reranker hook satisfies Principle VI.2; `citation_required` propagated to `SourceRef` (Principle VI.4); idempotent `result_id` supports VI.5 | ✅ |
| G6 Testing | Unit tests per pipeline component (10 test modules with mock retrievers); golden e2e integration test suite | ✅ |
| G7 Observability | Structured logging at Engine boundary (NFR-007); `RetrievalTrace` for step-level observability; Prometheus metrics extension points (NFR-016) | ✅ |
| G8 Security | No secrets in Engine core; `SQLRetriever` uses parameterized queries (Principle IX); `RetrievalQuery.query_text` is never interpolated into SQL | ✅ |
| G9 Performance | Async parallel strategy execution; `ExecutionPolicy` timeout prevents unbounded latency; hybrid meta-strategy eliminates unnecessary retriever composition overhead | ✅ |
| G10 Stack | Python 3.13, Pydantic v2, SQLAlchemy 2.x async, no deviations | ✅ |

*All gates pass. No complexity justification required.*

---

## Project Structure

### Documentation (this feature)

```text
specs/010-retrieval-engine-v2/
├── plan.md                  ← this file
├── research.md              ← Phase 0 output
├── data-model.md            ← Phase 1 output
├── quickstart.md            ← Phase 1 output
├── contracts/
│   └── pipeline-contract.md ← Phase 1 output
└── tasks.md                 ← Phase 2 output
```

### Source Code

```text
src/core/retrieval_engine/
├── __init__.py
├── models.py                  # ScoreSource, FusionAlgorithm, SkipReason,
│                              # SourceRef, RetrievalQuery, RetrievalContext,
│                              # ExpansionContext, ExpansionResult,
│                              # RawCandidate, RetrievedCandidate,
│                              # RetrievalStepTrace, RetrievalTrace,
│                              # RetrievalExecutionMetadata, RetrievalResult,
│                              # RetrievalEngineConfig
│                              # (StrategyType re-exported from core.retrieval_planner)
├── interfaces.py              # IRetrievalEngine, IRetriever, IQueryExpander,
│                              # IScoreFuser, IReranker
├── pipeline.py                # RetrievalEnginePipeline:
│                              #   schema check
│                              #   → expand (ExpansionContext → ExpansionResult)
│                              #   → resolve hybrid meta-strategy
│                              #   → build leg matrix (strategy × variant)
│                              #   → asyncio.gather all legs (with timeout + retry)
│                              #   → fuse raw results (IScoreFuser)
│                              #   → apply_candidate_cap (BudgetEnforcer)
│                              #   → rerank (IReranker)
│                              #   → apply_evidence_cap (BudgetEnforcer)
│                              #   → build RetrievedCandidate list (1-based ranks)
│                              #   → assemble trace (RetrievalTracer)
│                              #   → return frozen RetrievalResult
├── policies.py                # TimeoutPolicy, RetryPolicy, CancellationPolicy,
│                              # PartialResultPolicy, ExecutionPolicy (all frozen=True)
├── registry.py                # RetrieverRegistry: register/lookup for all 4 interface types;
│                              # build_pipeline(config, policy) → RetrievalEnginePipeline
├── router.py                  # StrategyRouter: StrategyType → IRetriever lookup
├── errors.py                  # RetrievalEngineError, SchemaMismatchError,
│                              # RetrieverNotFoundError, FusionError,
│                              # InsufficientCandidatesError, RetrievalConstraintViolation
├── expansion/
│   ├── __init__.py
│   └── passthrough.py         # PassthroughExpander: expand_type="passthrough";
│                              #   returns single variant = original query text
├── fusion/
│   ├── __init__.py
│   └── rrf.py                 # RRFScoreFuser: k=60 (configurable); dedup by chunk_id
├── reranking/
│   ├── __init__.py
│   └── passthrough.py         # PassthroughReranker: preserves fusion ordering
├── retrievers/
│   ├── __init__.py
│   ├── base.py                # BaseRetriever: retriever_id, supported_strategy,
│   │                          #   sequential_only=False, experimental=False;
│   │                          #   logging helpers
│   ├── dense.py               # DenseVectorRetriever  strategy="semantic"
│   ├── sparse.py              # SparseRetriever        strategy="keyword"
│   ├── metadata.py            # MetadataRetriever      strategy="metadata"
│   └── structured.py          # StructuredRetriever    strategy="structured"
│                              #   (tables, key-value, forms, structured blocks)
│                              # --- Optional / Experimental (not registered by default):
│   ├── graph.py               # GraphRetriever         strategy="graph" experimental=True
│   └── sql.py                 # SQLRetriever           strategy="sql"   experimental=True
├── budget/
│   ├── __init__.py
│   └── enforcer.py            # BudgetEnforcer: apply_candidate_cap,
│                              #   apply_evidence_cap, check_latency_budget
└── tracing/
    ├── __init__.py
    └── tracer.py              # RetrievalTracer: append_step, record_violation,
                               #   build_trace → RetrievalTrace (retry_count support)

src/fields/generic/retrieval_engine.yaml   # Generic: hybrid_components, enabled strategies,
                                           # RRF k, reranker backend, budget defaults
src/fields/legal/retrieval_engine.yaml     # Legal domain overrides
src/fields/pharmacy/retrieval_engine.yaml  # Pharmacy domain overrides
```

### Tests

```text
tests/unit/core/retrieval_engine/
├── __init__.py
├── conftest.py                # Shared fixtures: mock_retriever factory, mock_reranker,
│                              #   plan_builder, policy_builder (default + strict timeout
│                              #   + retry + no-partial), six named plan fixtures
├── test_models.py             # Frozen models; result_id determinism; schema_version;
│                              #   no infra imports in core (SC-004); ExecutionPolicy defaults
├── test_policies.py           # ExecutionPolicy: TimeoutPolicy, RetryPolicy,
│                              #   CancellationPolicy, PartialResultPolicy — field validation,
│                              #   defaults, frozen enforcement
├── test_router.py             # Registered strategy routes correctly; unregistered → error
├── test_budget_enforcer.py    # Candidate cap; evidence cap; latency check → partial=True
├── test_rrf_fuser.py          # RRF formula; dedup by chunk_id; single-list passthrough
├── test_query_expander.py     # PassthroughExpander: 1 variant; max_variants cap applied;
│                              #   ExpansionContext fields; ExpansionResult structure
├── test_dense_retriever.py    # DenseVectorRetriever with mock vector store
├── test_sparse_retriever.py   # SparseRetriever with mock FTS store
├── test_metadata_retriever.py # MetadataRetriever with mock metadata store
├── test_structured_retriever.py # StructuredRetriever with mock structured store
└── test_engine_pipeline.py    # Full pipeline tests:
                               #   US1: semantic single-strategy
                               #   US2: multi-strategy, hybrid meta-strategy expansion
                               #   US3: reranker ordering
                               #   US4: expansion N=3 variants
                               #   US5: timeout policy, retry policy
                               #   US6: custom retriever via registry
                               #   Empty strategy plan (SC-008)
                               #   InsufficientCandidatesError (allow_partial=False)

tests/integration/
└── test_retrieval_engine_e2e.py   # Golden suite: 14+ labelled plans with mock backends;
                                   # asserts RetrievalResult shape, dedup, trace completeness,
                                   # budget enforcement, hybrid expansion, policy behaviors
```

---

## Complexity Tracking

No Constitution Check violations. No complexity justifications required.

**Notable simplifications from architectural revisions**:

- **Hybrid removal**: Eliminating `HybridRetriever` removes one class (≈80 lines), one test
  module (≈60 lines), and one registry entry. The meta-strategy resolver in `pipeline.py`
  is ≈10 lines. Net reduction.
- **`RetrievalQuery` simplification**: Reduces from 8 fields to 3. Each leg's `RetrievalQuery`
  is now trivially constructible without copying plan state. `RetrievalContext` is built
  once and shared.
- **`ExecutionPolicy`**: Adds ≈60 lines of models (`policies.py`) but removes all hardcoded
  timeout/retry logic scattered across the pipeline. Net: more predictable, testable behavior.
- **`IQueryExpander` redesign**: `ExpansionContext` + `ExpansionResult` adds ≈30 lines of
  model code but makes the interface stable for all future expansion strategies without
  pipeline changes.
