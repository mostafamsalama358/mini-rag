# Implementation Plan: Architecture Refactor (behavior-preserving)

**Branch**: `003-architecture-refactor` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-architecture-refactor/spec.md`

## Summary

A behavior-preserving refactor of the AlgoRAG codebase that fixes structure, naming, and size without touching the frozen behavior contract (FR-001). It resolves the three biggest structural debts surfaced in the codebase audit:

1. **Misleading layer names** — `controllers/` holds application *services* (HTTP lives in `routes/`), and `models/` is a mixed bag of domain entities (`db_schemes/`, `enums/`) and data-access *repositories* (`*Model.py`).
2. **Oversized files** — 3 files exceed the 400 SLOC ceiling even after excluding blanks/comments/docstrings: `NLPController.py` (~547 SLOC), `PGVectorProvider.py` (~483), `core/retrieval/engine.py` (~443).
3. **Duplication / misplaced code** — deprecated re-export shims (`utils/retrieval.py`, `utils/structural_split.py`) still used by 5 callers; `utils/pharmacy_compat.py` is domain code in a cross-cutting package; `src/flowerconfig.py` duplicates `docker/flowerconfig.py`.

The refactor ships as **4 sequenced phases** (renames → splits → moves → dedup), each independently testable and revertible, with the full test suite green after every phase.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic, Celery, pgvector

**Storage**: PostgreSQL + pgvector (primary vector store); optional Qdrant via provider factory

**Testing**: pytest + pytest-asyncio; unit tests (`tests/unit/`); integration tests planned. Test **import lines may change**; **assertions may not**.

**Target Platform**: Linux server (Docker); local dev via Docker Compose (Postgres, broker, workers)

**Project Type**: Web service (FastAPI) + async worker fleet (Celery) + static SPA frontend

**Performance Goals**: No regression. p95 latency per endpoint MUST NOT increase beyond pre-refactor baseline (measured by existing metrics: `RAG_RETRIEVAL_LATENCY`, `RAG_RERANK_LATENCY`, `RAG_GENERATION_LATENCY`).

**Constraints**:
- Frozen contract (FR-001): every endpoint path/method/schema, Celery task **name** string + queue, CLI entrypoint, env-var, Prometheus metric name/label is byte-stable.
- SLOC ceiling (FR-002): ≤400 SLOC per file (executable + declarations; blanks/comments/docstrings excluded).
- No inward imports from infrastructure to core/domain.

**Scale/Scope**: ~11,260 LOC across ~110 Python files; 5 oversized files; 6 controllers, 5 repository files, 7 entity classes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Layer boundaries made explicit: `routes/` (presentation), `services/` (application), `repositories/` (data access), `models/db_schemes/`+`enums/` (domain entities), `stores/`+`utils/` (infrastructure). No inward imports introduced. | ☑ |
| G2 Feature-First | This is a cross-cutting refactor, not a feature slice. Justified below: the "feature" is structural health; changes are phase-isolated and each phase keeps the suite green. | ☑* |
| G3 SOLID / Plugins | SRP enforced via file splits; provider wiring stays in factories/`main.py`; no provider-specific code leaks into services. | ☑ |
| G4 Async + Types | Splits preserve `async` signatures and type hints; no public API downgrades. | ☑ |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, and citation code are **moved**, not altered (RAGService split keeps all 7 pipeline stages intact). | ☑ |
| G6 Testing | Full existing suite must pass after each phase unchanged in assertions; a contract-diff check guards FR-001. | ☑ |
| G7 Observability | Structured logging correlation ids and metric instrumentation preserved verbatim through splits. | ☑ |
| G8 Security | pgvector identifier allow-list preserved verbatim; no SQL parameterization weakened; no secrets introduced. | ☑ |
| G9 Performance | No work moved out of Celery workers into handlers; batching/pooling untouched. | ☑ |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker — unchanged. | ☑ |

*G2 is the only non-literal pass: a refactor is inherently cross-cutting. See Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-architecture-refactor/
├── plan.md              # This file
├── research.md          # Phase 0: rename/split/move decisions + alternatives
├── data-model.md        # Phase 1: layer/entity/responsibility map (no schema change)
├── quickstart.md        # Phase 1: per-phase validation runbook
├── contracts/           # Phase 1: frozen behavior contract (API + Celery + metrics)
│   └── frozen-behavior-contract.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root) — TARGET structure

The refactor moves the codebase to this shape. Items marked **(move)** or **(split)** change location/shape; everything else stays.

```text
src/
├── main.py                       # composition root (paths updated to renamed imports)
├── celery_app.py                 # unchanged (task NAMES/queues frozen)
├── celery_runtime.py             # unchanged
├── routes/                       # PRESENTATION (HTTP) — unchanged location
│   ├── base.py data.py nlp.py projects.py
│   └── schemes/                  # Pydantic request/response schemas
├── services/                     # APPLICATION LOGIC (controllers/ MERGES here)
│   ├── base.py                   # (move) from controllers/BaseController.py
│   ├── rag/                      # (split) NLPController + RAGService decomposed
│   │   ├── embedding.py          #   query embedding (sync+async)
│   │   ├── search.py             #   vector search + dense/sparse candidate fetch
│   │   ├── fusion.py             #   expansion + merge + dedupe orchestration
│   │   ├── enrichment.py         #   continuation + structural context enrichment
│   │   ├── prompt.py             #   prompt assembly + token budget
│   │   ├── answer_service.py     #   (was RAGService) full answer pipeline
│   │   └── rag_service.py        #   (was NLPController) collection mgmt + orchestration
│   ├── project_service.py        # (move+rename) controllers/ProjectController.py
│   ├── data_service.py           # (move+rename) controllers/DataController.py
│   ├── process_service.py        # (move+rename) controllers/ProcessController.py
│   ├── FieldRegistry.py          # unchanged location
│   └── __init__.py
├── repositories/                 # DATA ACCESS (split out of models/)
│   ├── base.py                   # (move) models/BaseDataModel.py
│   ├── project_repository.py     # (move+rename) models/ProjectModel.py
│   ├── chunk_repository.py       # (move+rename) models/ChunkModel.py
│   ├── asset_repository.py       # (move+rename) models/AssetModel.py
│   ├── chat_message_repository.py# (move+rename) models/ChatMessageModel.py
│   └── __init__.py
├── models/                       # DOMAIN ENTITIES ONLY (repositories removed)
│   ├── db_schemes/               # unchanged (SQLAlchemy entities + Alembic)
│   │   └── algorag/schemes/...
│   └── enums/                    # unchanged
├── core/                         # DOMAIN-AGNOSTIC PRIMITIVES (split oversized engines)
│   ├── retrieval/
│   │   ├── fusion.py             # (split) RRF + merge + dedupe
│   │   ├── rerank.py             # (split) rerank scoring
│   │   ├── focus.py              # (split) focus/continuation/detail heuristics
│   │   └── __init__.py           # re-export for stable `core.retrieval` API
│   ├── structural/
│   │   ├── articles.py           # (split) article number logic
│   │   ├── chapters.py           # (split) chapter/section logic
│   │   ├── patterns.py           # (split) StructuralPatterns + compiled regex
│   │   └── __init__.py
│   ├── chunking/                 # unchanged
│   └── query_understanding.py    # unchanged
├── fields/                       # CONFIGURATION (domain packs) — unchanged
├── stores/                       # INFRASTRUCTURE (providers)
│   ├── vectordb/providers/
│   │   ├── pgvector/             # (split) PGVectorProvider decomposed
│   │   │   ├── connection.py     #   extension setup + connection
│   │   │   ├── schema.py         #   DDL: create table/index/collection
│   │   │   ├── search.py         #   dense + sparse search queries
│   │   │   └── provider.py       #   (was PGVectorProvider) facade implementing interface
│   │   └── QdrantDBProvider.py   # unchanged
│   └── llm/                      # unchanged
├── tasks/                        # CELERY WORKERS — imports updated only
├── utils/                        # CROSS-CUTTING HELPERS ONLY
│   ├── pharmacy_compat.py        # (move) → fields/pharmacy/compat.py
│   ├── retrieval.py              # (DELETE) deprecated shim
│   └── structural_split.py       # (DELETE) deprecated shim
└── frontend/                     # out of scope (mount path unchanged)

tests/
├── unit/                         # import lines updated; assertions unchanged
└── contract/                     # (NEW) FR-001 contract-diff guard
```

**Structure Decision**:

- **`controllers/` → merges into existing `services/`** (not a new folder). The codebase already has `services/`; the controllers-are-services reality means they belong there. `services/rag/` sub-package isolates the RAG pipeline split so `services/` stays navigable.
- **`models/` is SPLIT, not renamed.** Audit finding: `models/` is mixed — it holds both domain entities (`db_schemes/`, `enums/`) and repositories (`*Model.py`). Renaming the whole folder to `repositories/` would misplace entities. Instead: repository files move to a new `repositories/` package; `models/` keeps `db_schemes/` + `enums/` as the pure domain layer.
- **`core/` engines are split internally** but keep stable package APIs (`core.retrieval`, `core.structural`) via `__init__.py` re-exports — so callers migrated off the `utils/` shims import from a stable namespace.
- **`stores/` providers split inside their own sub-package** (`pgvector/`), with a facade class preserving the `VectorDBInterface` contract.

## Phased Delivery (FR-011)

| Phase | Concern | Revertible unit | Suite-green gate |
|-------|---------|-----------------|------------------|
| P1 | Renames/moves: `controllers/`→`services/`, `models/*Model.py`→`repositories/`, `utils/pharmacy_compat.py`→`fields/pharmacy/` | one commit per layer | after all imports updated |
| P2 | Oversized-file splits: `NLPController`+`RAGService` → `services/rag/*`; `core/retrieval/engine.py` → `core/retrieval/*`; `core/structural/engine.py` → `core/structural/*`; `PGVectorProvider.py` → `stores/vectordb/providers/pgvector/*` | one commit per source file | after each split |
| P3 | Dedup: delete `utils/retrieval.py` + `utils/structural_split.py` shims; migrate all callers to `core.*`; consolidate `flowerconfig.py` | one commit | after migration |
| P4 | Docs sync: `src/ARCHITECTURE.md`, `docker/docker-compose.yml`, `AGENTS.md` path refs; add `tests/contract/` FR-001 guard | one commit | final |

## Complexity Tracking

> Filled because G2 (Feature-First) is a non-literal pass.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Cross-cutting refactor (not a single feature slice) | Naming/size/duplication debts span every layer; scoping to one slice would leave the codebase half-misleading and defeat User Story 1. | "Refactor only inside one feature" rejected: a partial rename (e.g., only `controllers/`→`services/` but `models/` stays mixed) leaves two layers contradicting each other and breaks the "names match responsibility" goal. Phasing (FR-011) is the mitigation — each phase is independently revertible. |
| Split `models/` instead of rename to `repositories/` | Audit showed `models/` mixes entities (`db_schemes/`, `enums/`) with repositories. | Blanket rename `models/`→`repositories/` rejected: it would move SQLAlchemy entities + Alembic migrations into a "repository" package — a worse mismatch than today, and would touch the Alembic `version_locations`/entry points (risk to frozen contract). Splitting keeps entities in `models/` and only moves the 5 repository files. |
