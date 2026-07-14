# Implementation Plan: Evidence Orchestrator

**Branch**: `011-evidence-orchestrator` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

## Summary

Build a generic, pluggable Evidence Orchestrator that sits between the Retrieval Engine
V2 (spec 010) and the Context Builder (spec 012). It consumes a `RetrievalResult` + the
originating `RetrievalPlan` and transforms them through a six-stage async pipeline
(collect → deduplicate → expand → compress-flag → prioritize → package) into a
normalized, deduplicated, ranked `EvidencePack`. Every stage is backed by a protocol
interface; concrete implementations live in `src/core/evidence_orchestrator/`
sub-packages and are wired via a lightweight registry. Domain behaviour is injected
through field-pack YAML config (`src/fields/generic/evidence_orchestrator.yaml`) with
the generic < domain < project override precedence established by spec 002.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: Pydantic 2.x (models + validation), `numpy` (cosine
similarity matrix for near-dedup), `tiktoken` optional (precise token counting);
FastAPI, SQLAlchemy 2.x async, Celery all available in the existing runtime.

**Storage**: No new tables. Reads existing chunk data via `ChunkRepository` (through a
thin `IChunkReader` interface) for expansion. `RetrievedCandidate.source_ref` carries
document/section metadata sufficient for citation construction.

**Testing**: `pytest` + `pytest-asyncio`; unit tests in `tests/unit/core/evidence_orchestrator/`;
integration test at `tests/integration/test_evidence_orchestrator_e2e.py`; benchmark
test with `pytest-benchmark` for SC-004 baseline measurement.

**Target Platform**: Linux server (Docker); same runtime environment as existing core.

**Project Type**: Internal library module — no HTTP routes in this spec; wired into
the RAG service by spec 012.

**Performance Goals**: Indicative ≤ 500 ms end-to-end for ≤ 100 candidates (baseline
measured at **p50 ≈ 7.9 ms / p95 ≈ 12 ms** on reference dev hardware via
`test_pipeline_latency_benchmark`; see research D9 and SC-004). Celery offload available
for sets exceeding configurable threshold (default 500 candidates).

**Constraints**: Must not introduce new external HTTP dependencies at orchestration
time (embedding reuse via existing `LLMProviderFactory`; character fallback available
when embedding is unavailable). No new DB migrations.

**Scale/Scope**: Primary load path: 10–100 `RetrievedCandidate` objects per query.
Deduplication near-duplicate batch limit: 200 candidates (configurable) before falling
back to character n-gram Jaccard.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked post-design below.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? | Notes |
|------|-------------|-------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ✅ | Orchestrator core in `src/core/evidence_orchestrator/`; `IChunkReader` defined in core; concrete `ChunkRepository` wiring in infrastructure layer |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ | All new code in `src/core/evidence_orchestrator/`; tests in `tests/unit/core/evidence_orchestrator/` |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ✅ | `IEvidenceCollector`, `IDeduplicator`, `IEvidenceExpander`, `IEvidencePrioritizer` are protocol ABCs; concrete impls registered via `EvidenceOrchestratorRegistry`; embedding reuse via existing `LLMProviderFactory` |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic schemas | ✅ | `IEvidenceExpander.expand()` and `IEvidencePrioritizer.prioritize()` are `async`; embedding batch call is async; all public models are frozen Pydantic; full type hints |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ | Every `EvidenceItem` carries a `Citation` object (doc_id, chunk_id, score, excerpt metadata); Orchestrator is the citation construction stage between retrieval and prompt |
| G6 Testing | Unit and integration tests planned for changed behavior | ✅ | Unit: dedup, prioritization fusion, expansion gate, compressibility scoring, pack assembly, empty-input handling; Integration: full pipeline e2e; Benchmark: latency baseline |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ | Structured log at each stage boundary: stage name, input count, output count, latency_ms, request_id, query_id; `pipeline_trace` embedded in `EvidencePack` |
| G8 Security | No secrets in code; input validation; parameterized SQL | ✅ | No new secrets; no SQL in orchestrator core; all inputs validated via Pydantic |
| G9 Performance | Long work in Celery; batching/pooling considered | ✅ | Sync async in-process for ≤ 500 candidates; Celery offload threshold configurable; embedding batch call batched per stage |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ | No deviation from mandated stack |

*All gates pass. No complexity justification required.*

**Post-design re-check**: Constitution gates confirmed after Phase 1 design. Interface
contracts, data model, and module structure all comply with G1–G10.

## Project Structure

### Documentation (this feature)

```text
specs/011-evidence-orchestrator/
├── plan.md              # This file
├── research.md          # Phase 0 — resolved design decisions (D1–D9)
├── data-model.md        # Phase 1 — entities, fields, relationships
├── quickstart.md        # Phase 1 — end-to-end validation guide
├── contracts/           # Phase 1 — interface contracts
│   ├── IEvidenceCollector.md
│   ├── IDeduplicator.md
│   ├── IEvidenceExpander.md
│   ├── ICompressibilityScorer.md
│   ├── IEvidencePrioritizer.md
│   └── EvidencePack.md
└── tasks.md             # Phase 2 — generated by /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── core/
│   └── evidence_orchestrator/
│       ├── __init__.py
│               ├── interfaces.py          # Protocol ABCs: IEvidenceCollector, IDeduplicator,
│       │                          # IEvidenceExpander, ICompressibilityScorer,
│       │                          # IEvidencePrioritizer, IChunkReader, ITokenCounter
│       ├── models.py              # EvidencePack, EvidenceItem, Citation,
│       │                          # EvidenceItemSource, OrchestratorTrace,
│       │                          # OrchestratorStageTrace, CollectedItem
│       ├── errors.py              # EvidenceOrchestratorError hierarchy
│       ├── config.py              # EvidenceOrchestratorConfig (Pydantic, extra=forbid)
│       ├── registry.py            # EvidenceOrchestratorRegistry (wires concrete impls)
│       ├── pipeline.py            # EvidenceOrchestrator.orchestrate() — main entry point
│       ├── collection/
│       │   ├── __init__.py
│       │   └── retrieval_result_collector.py  # IEvidenceCollector concrete impl
│       ├── deduplication/
│       │   ├── __init__.py
│       │   └── embedding_deduplicator.py      # IDeduplicator: exact + near-dup
│       ├── expansion/
│       │   ├── __init__.py
│       │   └── lineage_expander.py            # IEvidenceExpander: prev/next/parent
│       ├── compression/
│       │   ├── __init__.py
│       │   └── redundancy_scorer.py           # compressibility_score computation
│       ├── prioritization/
│       │   ├── __init__.py
│       │   └── fusion_prioritizer.py          # IEvidencePrioritizer: weighted fusion
│       ├── packaging/
│       │   ├── __init__.py
│       │   └── pack_assembler.py              # assembles & finalizes EvidencePack
│       └── token_counting/
│           ├── __init__.py
│           ├── character_approximation.py     # ITokenCounter: char/4 heuristic
│           └── tiktoken_counter.py            # ITokenCounter: tiktoken (optional)
│
└── fields/
    ├── generic/
    │   └── evidence_orchestrator.yaml         # generic field-pack config
    ├── pharmacy/
    │   └── evidence_orchestrator.yaml         # domain override (entity boost)
    └── legal/
        └── evidence_orchestrator.yaml         # domain override (recency boost)

tests/
├── unit/
│   └── core/
│       └── evidence_orchestrator/
│           ├── __init__.py
│           ├── conftest.py
│           ├── test_models.py
│           ├── test_collector.py
│           ├── test_deduplicator.py
│           ├── test_expander.py
│           ├── test_redundancy_scorer.py
│           ├── test_fusion_prioritizer.py
│           ├── test_pack_assembler.py
│           └── test_pipeline.py
└── integration/
    └── test_evidence_orchestrator_e2e.py
```

**Structure Decision**: Single-project layout following the established `src/core/<feature>/`
pattern. No new top-level project directories. No new FastAPI routes in this spec.

## Complexity Tracking

*No constitution violations. No entries required.*
