# Frozen Behavior Contract: Architecture Refactor (003)

**Date**: 2026-06-30 | **Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

> This is the **frozen contract** from spec FR-001. The refactor MUST NOT change anything listed here. A snapshot test under `tests/contract/` (see plan D6) asserts each item is byte-stable before vs. after every phase. **Internal class names, file names, module paths, and import lines are explicitly NOT frozen** — only the externally observable surfaces below.

---

## 1. HTTP API (Presentation contract)

Routes are registered in `src/main.py` and defined in `src/routes/*.py`. After the refactor, this surface MUST be identical:

| Router file | Prefix | Tags | Representative endpoints (path + method unchanged) |
|-------------|--------|------|------------------------------------------------------|
| `routes/base.py` | (base) | `api_v1` | base/health routes |
| `routes/projects.py` | `/api/v1/projects` | `api_v1`, `projects` | project CRUD + config |
| `routes/data.py` | `/api/v1/data` | `api_v1`, `data` | file/asset upload + processing |
| `routes/nlp.py` | `/api/v1/nlp` | `api_v1`, `nlp` | `/index/push`, `/index/search`, `/index/answer`, `/index/info` |

**Frozen for each endpoint**: HTTP method, path (incl. prefix), path params, request body schema (Pydantic models in `routes/schemes/`), response body shape, and status codes.

**Not frozen**: which internal service class a route instantiates (it will instantiate from `services/` instead of `controllers/`).

### Request/Response schemas (`routes/schemes/`)

The Pydantic models (`PushRequest`, `SearchRequest`, `AnswerRequest`, project/data schemas, etc.) are **frozen in field names and types**. `routes/schemes/` location is unchanged.

---

## 2. Celery contract

From `src/celery_app.py`:

| Item | Frozen value(s) |
|------|-----------------|
| App name | `algorag` |
| Task **names** (the dotted strings Celery calls + `task_routes` keys) | `tasks.file_processing.process_project_files`, `tasks.data_indexing.index_data_content`, `tasks.process_workflow.process_and_push_workflow`, `tasks.maintenance.clean_celery_executions_table`, `tasks.process_workflow.push_after_process_task` |
| Queues | `file_processing`, `data_indexing`, `default` (routing unchanged) |
| Beat schedule keys | `cleanup-old-task-records` |
| Serializers / acks_late / time limits | per current `celery_app.conf` |

**Not frozen**: the import paths the worker uses to *find* the task functions (those move when `controllers/`→`services/`), as long as Celery still resolves the same task **name**. The `@celery_app.task(name="...")` decorator `name=` strings MUST stay.

---

## 3. Configuration / environment contract (`helpers/config.py` → `Settings`)

Every `Settings` field name (env-var name) is frozen. Representative frozen vars: `POSTGRES_*`, `GENERATION_BACKEND`, `GENERATION_MODEL_ID`, `EMBEDDING_BACKEND`, `EMBEDDING_MODEL_ID`, `EMBEDDING_MODEL_SIZE`, `VECTOR_DB_BACKEND`, `RAG_*` (hybrid search, RRF, reranker, char budget, history mode, candidates, fetch multiplier), `CELERY_*`, `FILE_ALLOWED_TYPES`, `FILE_MAX_SIZE`, `PRIMARY_LANG`, `DEFAULT_LANG`.

**Not frozen**: internal helper function names inside `config.py`.

---

## 4. Observability contract (`utils/metrics.py`)

Prometheus metric **names and label names** are frozen. Representative: `RAG_RETRIEVAL_LATENCY` (labels: `project_id`), `RAG_RERANK_LATENCY` (`project_id`, `backend`), `RAG_GENERATION_LATENCY` (`project_id`), `RAG_RETRIEVAL_COUNT` (`project_id`, `query_type`), `RAG_RERANK_DOCS`, `RAG_RETRIEVAL_DOCS`, `RAG_TOP_SCORE`, `RAG_NO_CONTEXT_TOTAL`, `RAG_CLARIFICATION_TOTAL`, `RAG_RERANK_STARTUP_LATENCY` (`backend`, `stage`).

**Not frozen**: where these metrics are *emitted* within a file (emission moves with the split logic), as long as the same metric fires at the same pipeline stage.

---

## 5. Persistence / migration contract

| Item | Status |
|------|--------|
| Alembic `version_locations`, `env.py` metadata target | Frozen (stable path) |
| Existing migration revision hashes (`revision` / `down_revision`) | Frozen — historical, untouched |
| `RetrievedDocument` Pydantic fields (`text`, `score`, `metadata`) | Frozen |
| ORM entity table/column names (`Project`, `DataChunk`, `Asset`, `ChatMessage`, `ProjectPrompt`, `CeleryTaskExecution`) | Frozen |

**Not frozen**: which repository module queries an entity (moves `models/*Model.py`→`repositories/*_repository.py`).

---

## 6. Provider / plugin contract

| Interface | Frozen |
|-----------|--------|
| `VectorDBInterface` method signatures | Frozen |
| `LLMInterface` / provider method signatures | Frozen |
| Reranker `interface.py` + `get_reranker()` factory | Frozen |
| `FieldRegistry` / `FieldProfile` public API (from spec 002) | Frozen (FR-010) |

**Not frozen**: internal provider file layout (PGVector split into `pgvector/` sub-package).

---

## Contract guard

`tests/contract/test_frozen_contract.py` (new in P4) snapshots items 1–4 from the pre-refactor `main` branch and re-asserts after each phase. Items 5–6 are covered by the existing test suite passing unchanged.
