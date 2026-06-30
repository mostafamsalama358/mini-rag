# Data Model: Architecture Refactor (003)

**Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> ⚠️ **No database schema change.** This refactor is behavior-preserving (FR-001). No new tables, columns, migrations, or Alembic revisions are created. Alembic version files under `models/db_schemes/algorag/alembic/versions/` are **historical and untouched**; the `env.py` metadata target stays stable. This document describes the **code-layer responsibility model** (where each class/file lives after the refactor), which is the "data model" of a structural refactor.

---

## Layer / Responsibility Map (TARGET)

Each row is a Clean Architecture layer. "Inward imports allowed?" = may this layer import from a more-inner layer?

| Layer | Package(s) | Holds | Inward imports? |
|-------|-----------|-------|-----------------|
| Presentation | `routes/`, `routes/schemes/` | FastAPI handlers, Pydantic req/res schemas | may import inward (services, repositories, entities) |
| Application | `services/`, `services/rag/` | Use cases & orchestration (was `controllers/`); RAG pipeline; FieldRegistry | may import inward |
| Data Access | `repositories/` | SQLAlchemy query encapsulation (was `models/*Model.py`) | may import inward (entities) |
| Domain | `models/db_schemes/`, `models/enums/`, `core/` | ORM entities, enums, domain-agnostic RAG primitives | **no** inward imports |
| Infrastructure | `stores/`, `utils/`, `tasks/`, `fields/` | Provider impls, cross-cutting utils, Celery workers, domain config packs | implements interfaces defined in inner layers |

**Invariant (FR-007, NFR-001)**: No file in Domain (`core/`, `models/db_schemes/`, `models/enums/`, `fields/`) imports from Presentation, Application, or Infrastructure.

---

## Entities (unchanged — for reference)

These SQLAlchemy ORM classes live in `models/db_schemes/algorag/schemes/` and are **not moved**. Listed only to anchor the repository mapping below.

| Entity | File (unchanged) | Repositories that query it (after move) |
|--------|------------------|------------------------------------------|
| `Project` | `schemes/project.py` | `repositories/project_repository.py` (was `ProjectModel.py`) |
| `DataChunk` | `schemes/datachunk.py` | `repositories/chunk_repository.py` (was `ChunkModel.py`) |
| `Asset` | `schemes/asset.py` | `repositories/asset_repository.py` (was `AssetModel.py`) |
| `ChatMessage` | `schemes/chatmessage.py` | `repositories/chat_message_repository.py` (was `ChatMessageModel.py`) |
| `ProjectPrompt` | `schemes/project_prompt.py` | queried via `project_repository.py` |
| `RetrievedDocument` | `schemes/datachunk.py` (Pydantic) | passed by value through pipeline; no repository |
| `CeleryTaskExecution` | `schemes/celery_task_execution.py` | queried via `utils/idempotency_manager.py` (stays) |

---

## Repository File Mapping (P1 move)

| From (`models/`) | To (`repositories/`) | Class (unchanged) |
|------------------|----------------------|-------------------|
| `BaseDataModel.py` | `base.py` | `BaseDataModel` |
| `ProjectModel.py` | `project_repository.py` | `ProjectModel` |
| `ChunkModel.py` | `chunk_repository.py` | `ChunkModel` |
| `AssetModel.py` | `asset_repository.py` | `AssetModel` |
| `ChatMessageModel.py` | `chat_message_repository.py` | `ChatMessageModel` |

Class names stay (`ProjectModel` etc.) to keep the diff a pure move; only the module path changes (see research D2).

---

## Service File Mapping (P1 move + P2 split)

### P1 — simple moves into `services/`

| From (`controllers/`) | To (`services/`) | Class (unchanged) |
|----------------------|------------------|-------------------|
| `BaseController.py` | `base.py` | `BaseController` |
| `ProjectController.py` | `project_service.py` | `ProjectController` |
| `DataController.py` | `data_service.py` | `DataController` |
| `ProcessController.py` | `process_service.py` | `ProcessController` (+ `Document` dataclass) |

### P2 — RAG pipeline split into `services/rag/`

`NLPController.py` (~547 SLOC) + `RAGService.py` decompose by responsibility. The orchestrator class `NLPController` remains the public entry used by `routes/nlp.py` and `tasks/`; internal methods move to sibling modules and are called by the orchestrator.

| New module (`services/rag/`) | Responsibility | Origin (methods moved from) |
|------------------------------|----------------|------------------------------|
| `embedding.py` | query embedding (sync + async thread-offload) | `NLPController._embed_query`, `_embed_query_async`, `_embed_primary_query` |
| `search.py` | vector search + concurrent dense/sparse candidate fetch | `NLPController._vector_search`, `_fetch_dense_and_sparse_candidates`, `search_vector_db_collection` |
| `fusion.py` | expansion-query build + merge + dedupe orchestration (delegates to `core.retrieval`) | `NLPController._run_expansion_and_merge` |
| `enrichment.py` | continuation chunks + structural context enrichment | `NLPController.enrich_retrieved_documents`, `_expand_structural_context`, `_append_chunk_if_new` |
| `prompt.py` | document-text focus + token-budget trimming | `RAGService._document_text_for_prompt` + budget loop |
| `answer_service.py` | full answer pipeline (was `RAGService`) | `RAGService.answer_question` |
| `rag_service.py` | collection mgmt + answer orchestration facade (was `NLPController`) | `NLPController` collection methods + `answer_rag_question` |

---

## Infrastructure File Mapping (P2 split)

### `stores/vectordb/providers/PGVectorProvider.py` (~483 SLOC) → `stores/vectordb/providers/pgvector/`

| New module | Responsibility | Notes |
|------------|----------------|-------|
| `connection.py` | `connect()`, pgvector extension setup | — |
| `schema.py` | table/index/collection DDL | **`_validate_identifier` + `_IDENTIFIER_RE` preserved verbatim** (security: NFR-007) |
| `search.py` | dense + sparse search SQL queries | parameterized; no string-concatenated user input |
| `provider.py` | `PGVectorProvider(VectorDBInterface)` facade | delegates to the three above; contract unchanged |

### `core/retrieval/engine.py` (~443 SLOC) → `core/retrieval/` (internal split, stable package API)

| New module | Responsibility |
|------------|----------------|
| `fusion.py` | `hybrid_rrf`, `merge_retrieved_documents`, `deduplicate_retrieved_documents` |
| `rerank.py` | `rerank_retrieved_documents`, `sort_documents_for_prompt` |
| `focus.py` | continuation/detail/comparison/exhaustive heuristics, `_source_key` |
| `__init__.py` | re-exports all public names → `from core.retrieval import X` works |

`core/retrieval/engine.py` may be kept as a thin re-export during P3 migration, then deleted (mirrors shim strategy) — decided at P3.

### `core/structural/engine.py` (~325 SLOC) — stays single file (<400), re-exported via `__init__.py`.

---

## Validation Rules (code-level, enforced in P2/P4)

- **Size**: every `.py` under `src/` ≤ 400 SLOC (executable + declarations; blanks/comments/docstrings excluded). Checked by a counter in P4.
- **Boundaries**: `grep -rn "^from (routes|services|repositories|stores|utils|tasks)\." src/core/ src/models/db_schemes/ src/models/enums/ src/fields/` returns **zero** hits.
- **No inward imports**: infrastructure implements interfaces; factories wire providers (NFR-003).

## State Transitions

Not applicable — no entity lifecycle changes. The only "state" is the codebase structure, which transitions phase by phase per FR-011, each phase ending green.
