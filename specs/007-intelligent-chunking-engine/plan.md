# Implementation Plan: Intelligent Chunking Engine

**Branch**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-intelligent-chunking-engine/spec.md`

---

## Summary

Replace `map_elements_to_chunks` (adjacent same-type grouping heuristic) with a
**strategy-based Intelligent Chunking Engine** that operates exclusively on the Canonical
Document Model produced by `006-document-intelligence-pipeline`. The engine routes every
adjacent element boundary through a Semantic Boundary Evaluator (11 independent signal fields →
`BoundaryFeatures`) and a swappable Boundary Decision Policy (deterministic rule-based default →
`BoundaryDecision`), then assembles chunks via a stateful Chunk Builder that assigns stable
identity, parent/child/prev/next relationships, lineage, and structural context — all validated
by a dedicated Chunk Validation stage that produces an explicit `ValidationReport`. Output is
additive and backward-compatible with existing indexing/retrieval/storage contracts.

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic v2, Celery

**Storage**: PostgreSQL + pgvector (primary); chunk relationships/lineage stored as additive
JSONB keys in `DataChunk.chunk_metadata` — no schema migration required

**Testing**: pytest + pytest-asyncio; unit tests (`tests/unit/chunking/`), integration tests
(`tests/integration/chunking/`), benchmark tests (`tests/integration/benchmarks/`)

**Target Platform**: Linux server (Docker + Celery workers)

**Project Type**: Web-service backend (RAG ingestion pipeline)

**Performance Goals**: New engine ≤ 2× current `map_elements_to_chunks` median per-document
wall-clock time (SC-008; baseline recorded in `tests/integration/benchmarks/chunking_baseline.json`)

**Constraints**:
- Fully deterministic and reproducible (FR-030/FR-014); no wall-clock time, randomness, or live
  model calls in default strategies
- Additive metadata only — existing chunk storage schema untouched (FR-031/FR-032)
- No domain-specific Python in core — all behavioral differences via YAML pack configuration

**Scale/Scope**: Per-asset chunking in Celery worker; replaces one call site in
`tasks/file_processing.py`; adds ~8 new source files in `src/core/chunking/`

---

## Constitution Check

*Reference: `.specify/memory/constitution.md` v1.0.0*

| Gate | Requirement | Pass? | Notes |
|------|-------------|-------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ✅ | Chunking engine in `core/chunking/` (application layer); Celery tasks unchanged; no infrastructure imports in core |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ | `core/chunking/` is self-contained; tests co-located in `tests/unit/chunking/` and `tests/integration/chunking/` |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ✅ | `ChunkingStrategy` ABC + registry factory; `BoundaryDecisionPolicy` Protocol + registry; new strategies/policies addable without modifying dispatch |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic schemas | ✅ | Chunking is CPU-bound; runs in Celery workers (existing async boundary); all public models are Pydantic v2; no blocking I/O |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations | N/A | This feature is at the ingestion/chunking layer, upstream of retrieval; G5 rules apply to the RAG answer path (see Complexity Tracking) |
| G6 Testing | Unit and integration tests planned for changed behavior | ✅ | 9 validation scenarios in `quickstart.md`; boundary/merge/split, relationships, lineage, determinism, validation gate, serialization, performance, lifecycle all covered |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ | Per-asset chunk counts by element type, validation rule pass/fail counts, strategy applied — logged at Celery task boundary (NFR-007) |
| G8 Security | No secrets in code; input validation; parameterized SQL | ✅ | No new credentials; `DocumentModel`/`StructuralElement` validated by Pydantic on construction; no new SQL |
| G9 Performance | Long work in Celery; batching/pooling considered | ✅ | Chunking already runs in Celery workers; new engine is O(N) per element; no new blocking calls |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ | No new stack additions; all new code is pure Python + Pydantic |

---

## Project Structure

### Documentation (this feature)

```text
specs/007-intelligent-chunking-engine/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — 9 decisions (R1–R9)
├── data-model.md        # Phase 1 output — 13 entities + interfaces
├── quickstart.md        # Phase 1 output — 9 validation scenarios
├── contracts/
│   ├── chunking-strategy-contract.md
│   ├── boundary-decision-policy-contract.md
│   └── chunk-output-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (changes from repo root)

```text
src/
├── core/
│   ├── document_intelligence/
│   │   └── model.py                      # ~ extend StructuralElementType Literal (+4 types)
│   └── chunking/
│       ├── __init__.py                   # + export public API
│       ├── engine.py                     # ~ keep existing shims; add orchestration entry point
│       ├── models.py                     # + BoundaryCandidate, BoundaryFeatures, BoundaryDecision,
│       │                                 #   ChunkLineage, ChunkIdentity, ChunkRelationships,
│       │                                 #   StructuralContext, Chunk (extended), ChunkSet,
│       │                                 #   ValidationReport, ChunkingStrategyConfig
│       ├── interfaces.py                 # + ChunkingStrategy ABC, BoundaryDecisionPolicy Protocol
│       ├── registry.py                   # + strategy + policy registry + factory functions
│       ├── evaluator.py                  # + SemanticBoundaryEvaluator (11 signal fields)
│       ├── builder.py                    # + ChunkBuilder (stateful lifecycle)
│       ├── validator.py                  # + ChunkValidator (6 quality rules → ValidationReport)
│       └── strategies/
│           ├── __init__.py               # + auto-register default strategy + policy
│           └── semantic_structural.py   # + SemanticStructuralChunkingStrategy
│                                        #   + RuleBasedBoundaryDecisionPolicy
├── fields/
│   ├── schemas.py                        # ~ ChunkingProfile gains `strategy`, `policy` fields
│   └── generic/
│       └── chunking.yaml                 # ~ add `strategy: semantic_structural`, `policy: rule_based`
└── tasks/
    └── file_processing.py                # ~ replace map_elements_to_chunks call with strategy.chunk()

tests/
├── fixtures/
│   └── chunking/
│       ├── heading_table_sections.py     # + Scenario 1 fixture DocumentModel
│       └── extended_types.py            # + Scenario 5 fixture DocumentModel
├── unit/
│   └── chunking/
│       ├── test_semantic_boundaries.py   # + Scenario 1
│       ├── test_relationships.py         # + Scenario 3
│       ├── test_determinism.py           # + Scenario 4
│       ├── test_extended_types.py        # + Scenario 5
│       ├── test_validation.py            # + Scenario 6
│       ├── test_serialization.py         # + Scenario 7
│       └── test_builder_lifecycle.py    # + Scenario 9
└── integration/
    ├── chunking/
    │   └── test_strategy_swap.py         # + Scenario 2
    └── benchmarks/
        ├── chunking_baseline.json        # + baseline recording
        └── test_chunking_benchmark.py    # + Scenario 8
```

**Legend**: `+` = new file/directory; `~` = modified existing file

**Structure Decision**: Single-project layout (existing `src/` monorepo). Chunking engine
lives entirely within `core/chunking/` — the correct Clean Architecture layer for application-
level, domain-agnostic business logic. No new top-level project or service added.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| G5 N/A — not a retrieval feature | Chunking is the ingestion stage; G5's hybrid-retrieval, reranking, and prompt-versioning rules govern the answer path. Chunking output feeds indexing unchanged. | Marking G5 as failing would be a false violation; the gate is not applicable to this feature's scope. |
| Two registries (strategy + policy) | Each registry governs an independently swappable component at a different level (whole strategy vs. per-strategy policy). A single combined registry would conflate the interfaces and violate the Boundary Decision Pipeline's separation of concerns. | Collapsing both into one registry was considered and rejected because it would couple ChunkingStrategy selection to BoundaryDecisionPolicy selection, preventing a strategy from bundling its own default policy while still allowing external override. |
