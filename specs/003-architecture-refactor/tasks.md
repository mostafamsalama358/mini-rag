# Tasks: Architecture Refactor (behavior-preserving)

**Input**: Design documents from `/specs/003-architecture-refactor/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/frozen-behavior-contract.md, quickstart.md

**Tests**: Per constitution (Principle VII), tests are required for changed behavior. However, this is a **behavior-preserving refactor** — the existing test suite IS the regression net (assertions unchanged). New test work is limited to (a) a frozen-contract guard and (b) import-line fixes. Test **import lines may change; assertions may not** (spec Assumption).

**Organization**: Tasks are grouped by the 4 delivery phases (FR-011), with user-story labels mapping each task to the spec story it satisfies. Phase order is mandatory: P1 renames → P2 splits → P3 dedup → P4 polish. Each phase ends green (Checks A/B/C from quickstart.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Spec user story this task satisfies (US1–US5). Setup/foundational/dedup/polish tasks carry NO story label (they serve all stories).
- Every task lists an exact file path

## Path Conventions

- Source: `src/` at repository root
- Tests: `tests/` at repository root
- Frozen contract reference: `specs/003-architecture-refactor/contracts/frozen-behavior-contract.md`
- Validation runbook: `specs/003-architecture-refactor/quickstart.md` (Checks A=suite, B=contract, C=boundaries)

---

## Phase 1: Setup (Baseline & Guard Scaffolding)

**Purpose**: Capture the frozen contract snapshot and stand up the regression net BEFORE any code moves.

- [ ] T001 Generate the frozen-contract snapshot from `main` branch: capture FastAPI route table (paths/methods/prefix/tags), Celery task `name=` strings + `task_routes` keys + queues, `Settings` env-var names, and Prometheus metric/label names from `src/utils/metrics.py` — store as the baseline for `tests/contract/`
- [ ] T002 Record the baseline green run count on `main`: run `pytest -q` and save the passing/failing count as the bar every phase must meet (documented in `specs/003-architecture-refactor/quickstart.md`)
- [ ] T003 Create the contract guard test scaffold in `tests/contract/__init__.py` and `tests/contract/test_frozen_contract.py` that loads the T001 snapshot and asserts route table + Celery names + Settings fields + metric names are unchanged (initially may be skipped until P4 wires the snapshot; scaffold now so P1 can extend it)

**Checkpoint**: Baseline captured, guard scaffold present. No source code changed yet.

---

## Phase 2: Foundational (Layer Packages)

**Purpose**: Create the empty target packages so subsequent move/split tasks have destinations. No logic yet.

- [ ] T004 [P] Create `src/repositories/__init__.py` (empty package for data-access repositories split from `src/models/`)
- [ ] T005 [P] Create `src/services/rag/__init__.py` (empty sub-package for the RAG pipeline split target)
- [ ] T006 [P] Create `src/stores/vectordb/providers/pgvector/__init__.py` (empty sub-package for the PGVector split target)
- [ ] T007 [P] Create `src/core/retrieval/__init__.py` shim entry (already exists — verify; will host re-exports after split) and `src/core/structural/__init__.py` (verify exists)

**Checkpoint**: Target packages exist. Suite still green.

---

## Phase 3: User Story 1 + 4 — Renames & Moves (Priority: P1)

**Goal** (US1 + US4): Misleading layer names resolved; misplaced/duplicated code relocated. The layer currently called `controllers/` (application services) merges into `services/`; `models/` is split so repositories move to `repositories/` while entities stay; domain code leaves `utils/`.

**Independent Test**: Run quickstart.md Checks A (suite green), B (contract unchanged), C (no inward imports). A reviewer reading folder names can tell HTTP handlers (`routes/`) from application logic (`services/`) from data access (`repositories/`) from entities (`models/db_schemes/`).

> Class names are KEPT (only module paths move) to keep the diff a pure move (research D1/D2). After this phase, `src/controllers/` must not exist; `src/models/` must contain only `db_schemes/`, `enums/`, `__init__.py`.

- [ ] T008 [US1] Move `src/controllers/BaseController.py` → `src/services/base.py`; keep class `BaseController`; update its internal docstring path reference
- [ ] T009 [US1] Move `src/controllers/ProjectController.py` → `src/services/project_service.py`; keep class `ProjectController`
- [ ] T010 [P] [US1] Move `src/controllers/DataController.py` → `src/services/data_service.py`; keep class `DataController`
- [ ] T011 [P] [US1] Move `src/controllers/ProcessController.py` → `src/services/process_service.py`; keep classes `ProcessController` and `Document`
- [ ] T012 [US1] Update all `from controllers.*` imports to `from services.*` across: `src/routes/data.py`, `src/routes/nlp.py`, `src/routes/projects.py`, `src/tasks/data_indexing.py`, `src/tasks/file_processing.py`, `src/stores/vectordb/VectorDBProviderFactory.py` (imports `BaseController`), and `src/services/__init__.py`
- [ ] T013 [US1] Delete `src/controllers/` directory once empty; remove any `controllers` references in `src/controllers/__init__.py` migration
- [ ] T014 [US1] Move `src/models/BaseDataModel.py` → `src/repositories/base.py`; keep class `BaseDataModel`
- [ ] T015 [P] [US1] Move `src/models/ProjectModel.py` → `src/repositories/project_repository.py`; keep class `ProjectModel`
- [ ] T016 [P] [US1] Move `src/models/ChunkModel.py` → `src/repositories/chunk_repository.py`; keep class `ChunkModel`
- [ ] T017 [P] [US1] Move `src/models/AssetModel.py` → `src/repositories/asset_repository.py`; keep class `AssetModel`
- [ ] T018 [P] [US1] Move `src/models/ChatMessageModel.py` → `src/repositories/chat_message_repository.py`; keep class `ChatMessageModel`
- [ ] T019 [US1] Update all `from models.*Model import` imports to `from repositories.*_repository import` across `src/routes/`, `src/services/`, `src/tasks/`, and `src/stores/` (NOT `models.db_schemes` or `models.enums` — those stay). Preserve the lazy imports inside `src/repositories/project_repository.py` that reference `models.db_schemes.ProjectPrompt`
- [ ] T020 [US1] Verify `src/models/` now contains only `db_schemes/`, `enums/`, `__init__.py`; confirm `src/models/__init__.py` no longer re-exports the moved repository classes
- [ ] T021 [US4] Move `src/utils/pharmacy_compat.py` → `src/fields/pharmacy/compat.py`; update all its callers (grep `pharmacy_compat`) to import from `fields.pharmacy.compat`
- [ ] T022 [US4] Consolidate Flower config: keep `src/flowerconfig.py` as single source of truth; delete `docker/flowerconfig.py`; update `docker/docker-compose.yml` to reference the surviving copy and verify Flower still resolves it
- [ ] T023 [US1] Run Checks A/B/C; fix any import errors. Commit P1 as one revertible unit per the phased rule

**Checkpoint**: Layer names match responsibilities; `controllers/` gone; `models/` is entities-only; domain code out of `utils/`. Suite + contract green.

---

## Phase 4: User Story 2 + 1 — Oversized-File Splits (Priority: P1)

**Goal** (US2 + US1): No source file exceeds 400 SLOC. Each oversized file splits along pre-existing responsibility seams — pure moves, no logic change.

**Independent Test**: An SLOC counter reports zero files >400 SLOC under `src/`. Each previously-oversized file's pieces are named, single-responsibility, and <400 SLOC. The RAG pipeline still emits the same metrics at the same stages (Check B).

> Class names and public APIs are kept. Splits use facade classes + `__init__.py` re-exports so external import paths stay stable during migration. Security invariant: `_validate_identifier` + `_IDENTIFIER_RE` preserved verbatim in the pgvector split (NFR-007).

### 4a — RAG pipeline split (`src/services/rag/`)

- [ ] T024 [US2] Split embedding logic out of the NLP orchestrator into `src/services/rag/embedding.py`: move `_embed_query`, `_embed_query_async`, `_embed_primary_query` (methods become module functions taking the embedding client, OR a small `QueryEmbedder` helper; orchestrator delegates)
- [ ] T025 [US2] Split vector search into `src/services/rag/search.py`: move `_vector_search`, `_fetch_dense_and_sparse_candidates`, `search_vector_db_collection`
- [ ] T026 [US2] Split expansion/fusion orchestration into `src/services/rag/fusion.py`: move `_run_expansion_and_merge` (delegates to `core.retrieval` algorithms)
- [ ] T027 [US2] Split enrichment into `src/services/rag/enrichment.py`: move `enrich_retrieved_documents`, `_expand_structural_context`, `_append_chunk_if_new`
- [ ] T028 [US2] Move the collection-management orchestrator into `src/services/rag/rag_service.py`: `index_into_vector_db`, `reset_vector_db_collection`, `get_vector_db_collection_info`, `create_collection_name`, `build_profile_for_project`, `answer_rag_question` (this is the `NLPController` facade that delegates to T024–T027)
- [ ] T029 [US2] Move the answer pipeline into `src/services/rag/answer_service.py`: the former `RAGService.answer_question` (now `src/services/RAGService.py` after P1) and extract the prompt-focus + token-budget helper into `src/services/rag/prompt.py` (`_document_text_for_prompt` + budget loop)
- [ ] T030 [US2] Update `src/routes/nlp.py`, `src/tasks/data_indexing.py`, `src/tasks/file_processing.py` to import the `NLPController`/`RAGService` classes from `services.rag.*`; verify metric emission points (`RAG_RETRIEVAL_LATENCY`, `RAG_RERANK_LATENCY`, `RAG_GENERATION_LATENCY`) fire at the same stages
- [ ] T031 [US2] Run SLOC check on each new `services/rag/*.py`; if any exceeds 400 SLOC, split further along responsibility seams. Run Checks A/B/C

### 4b — `core/retrieval/engine.py` split

- [ ] T032 [P] [US2] Split fusion algorithms into `src/core/retrieval/fusion.py`: `hybrid_rrf`, `merge_retrieved_documents`, `deduplicate_retrieved_documents`
- [ ] T033 [P] [US2] Split rerank helpers into `src/core/retrieval/rerank.py`: `rerank_retrieved_documents`, `sort_documents_for_prompt`
- [ ] T034 [P] [US2] Split focus/continuation heuristics into `src/core/retrieval/focus.py`: continuation + detail/comparison/exhaustive heuristics, `_source_key`
- [ ] T035 [US2] Populate `src/core/retrieval/__init__.py` to re-export every public name from `fusion.py`, `rerank.py`, `focus.py` so `from core.retrieval import X` works (stable package API per research D3)
- [ ] T036 [US2] Delete the now-empty `src/core/retrieval/engine.py` (or keep as thin re-export to be deleted in Phase 5 per shim strategy — decide here, execute in Phase 5)
- [ ] T037 [US2] Run Checks A/B/C; confirm `core.retrieval` callers still resolve

### 4c — PGVector provider split

- [ ] T038 [P] [US2] Split connection into `src/stores/vectordb/providers/pgvector/connection.py`: `connect()`, pgvector extension setup
- [ ] T039 [P] [US2] Split schema/DDL into `src/stores/vectordb/providers/pgvector/schema.py`: table/index/collection DDL — **preserve `_validate_identifier` and `_IDENTIFIER_RE` verbatim** (security invariant, NFR-007)
- [ ] T040 [P] [US2] Split search queries into `src/stores/vectordb/providers/pgvector/search.py`: dense + sparse search SQL (parameterized; no string-concatenated user input)
- [ ] T041 [US2] Create `src/stores/vectordb/providers/pgvector/provider.py`: `PGVectorProvider(VectorDBInterface)` facade that delegates to connection/schema/search; contract unchanged
- [ ] T042 [US2] Update `src/stores/vectordb/VectorDBProviderFactory.py` to import `PGVectorProvider` from the new `pgvector.provider` path
- [ ] T043 [US2] Delete the old monolith `src/stores/vectordb/providers/PGVectorProvider.py`; run Checks A/B/C

**Checkpoint**: 0 files >400 SLOC under `src/`. `core/structural/engine.py` (~325 SLOC) and `src/services/FieldRegistry.py` (~371 SLOC) intentionally NOT split (already under budget — research D3). Suite + contract green.

---

## Phase 5: User Story 4 — Deduplication (Priority: P2)

**Goal** (US4): No two places implement the same logic. Deprecated re-export shims deleted; all callers migrated to the real modules.

**Independent Test**: `grep` for the old shim imports returns zero hits across `src/` and `tests/`. Exactly one definition of each algorithm exists.

- [ ] T044 [US4] Migrate `src/services/rag/answer_service.py` (post-P2 `RAGService`) to import retrieval helpers from `core.retrieval` / `core.structural` instead of `utils.retrieval` / `utils.structural_split`
- [ ] T045 [P] [US4] Migrate `src/services/rag/rag_service.py` (post-P2 `NLPController`) off the shims to `core.retrieval` / `core.structural`
- [ ] T046 [P] [US4] Migrate `src/services/process_service.py` (post-P1 `ProcessController`) off the shims to `core.structural`
- [ ] T047 [US4] Migrate all `tests/unit/` and `tests/conftest.py` imports off the shims (import lines only; assertions unchanged) — verify via grep that no `from utils.retrieval` or `from utils.structural_split` remains
- [ ] T048 [US4] Delete `src/utils/retrieval.py` and `src/utils/structural_split.py` (the deprecated re-export shims)
- [ ] T049 [US4] If `src/core/retrieval/engine.py` was kept as a thin re-export in T036, delete it now; ensure all imports use `core.retrieval` package
- [ ] T050 [US4] Run Checks A/B/C; grep confirms zero shim references

**Checkpoint**: Single source of truth for every algorithm. No lingering re-exports. Suite + contract green.

---

## Phase 6: Polish & Cross-Cutting (Priority: P3)

**Purpose**: Documentation sync, boundary enforcement, and the contract guard — serves US1, US3, US5.

- [ ] T051 [US1] Update `src/ARCHITECTURE.md` to reflect renamed layers: `controllers/`→`services/`, repository split from `models/`, RAG pipeline in `services/rag/`, pgvector in `stores/vectordb/providers/pgvector/`. Verify every path mentioned exists on disk
- [ ] T052 [P] Update `AGENTS.md` and `LEAN-CTX.md` path references if they mention moved modules
- [ ] T053 [P] [US5] Add the layer-boundary guard: a test/script asserting no file under `src/core/`, `src/models/db_schemes/`, `src/models/enums/`, `src/fields/` imports from `routes`, `services`, `repositories`, `stores`, `utils`, or `tasks` (Check C automated) in `tests/contract/test_layer_boundaries.py`
- [ ] T054 [US5] Wire the full `tests/contract/test_frozen_contract.py` (T003 scaffold) to assert the T001 snapshot: route table, Celery task names/queues, Settings fields, metric names all match baseline
- [ ] T055 [P] Add an SLOC guard test/script in `tests/contract/test_file_size.py` that fails if any `src/**/*.py` exceeds 400 SLOC (executable+declarations; blanks/comments/docstrings excluded) — codifies SC-001/SC-002
- [ ] T056 [US3] Final full-suite run (`pytest -q`) and confirm the passing count matches the T002 baseline (no assertion changes); run quickstart.md end-to-end validation
- [ ] T057 [US1] Verify a reviewer unfamiliar with the code can locate HTTP handlers, RAG orchestration, data access, DB entities, and provider wiring from names/folders alone (Success Criterion SC-006) — manual check, record result

**Checkpoint**: Docs match reality; contract, boundary, and size guards automated; suite green at baseline count. Refactor complete.

---

## Dependencies & Execution Order

### Phase Dependencies (STRICT — FR-011)

- **Phase 1 (Setup)**: No dependencies — captures baseline before any change
- **Phase 2 (Foundational)**: Depends on Phase 1 — creates empty target packages
- **Phase 3 (Renames/Moves)**: Depends on Phase 2 — moves into the new packages
- **Phase 4 (Splits)**: Depends on Phase 3 — splits operate on final post-rename paths
- **Phase 5 (Dedup)**: Depends on Phase 4 — shim deletion requires the `core/` re-export stability from 4b
- **Phase 6 (Polish)**: Depends on Phase 5 — docs/guards reflect final structure

> ⚠️ Phases are **sequential**, not parallel. Rationale (research D7): renames must land before splits (so splits operate on final paths), and shim deletion must follow core re-export stability. Each phase is an independent revertible commit.

### User Story Coverage

| Story | Priority | Phases | Independent test |
|-------|----------|--------|------------------|
| US1 — Code where you expect it | P1 | 2, 3, 6 | Folder names alone identify each layer (T057) |
| US2 — One responsibility per file | P1 | 4 | SLOC check: 0 files >400 SLOC (T031, T055) |
| US3 — Zero behavior change | P1 | 1, 6 | Suite + contract guard green at baseline (T054, T056) |
| US4 — No duplicated logic | P2 | 3, 5 | grep: zero shim refs; single source of truth (T050) |
| US5 — New capability has a clear home | P3 | 6 | Boundary guard passes (T053) |

### Within Each Phase

- File moves before import updates
- Import updates before deletion of the old location
- Each phase ends with Checks A/B/C green before advancing

### Parallel Opportunities (within a phase only)

- Phase 2: T004–T007 all parallel (distinct empty packages)
- Phase 3: T010/T011 parallel (distinct controllers); T015–T018 parallel (distinct repositories); T021/T022 parallel
- Phase 4: T032–T034 parallel (distinct core splits); T038–T040 parallel (distinct pgvector splits)
- Phase 5: T044–T046 parallel (distinct migrated modules)
- Phase 6: T052/T053/T055 parallel (distinct guard files)

---

## Implementation Strategy

### MVP First (Phases 1–3)

1. Complete Phase 1: capture baseline + guard scaffold
2. Complete Phase 2: create empty packages
3. Complete Phase 3: renames & moves (US1 + US4 partial)
4. **STOP and VALIDATE**: Checks A/B/C green — layer names now match responsibilities

### Incremental Delivery

1. Phases 1–3 → layer structure correct (US1 mostly done)
2. Add Phase 4 → size goal met (US2 done)
3. Add Phase 5 → duplication removed (US4 done)
4. Add Phase 6 → docs + guards (US3, US5 done; full SC coverage)
5. Each phase adds structural health without breaking behavior

### Single-Developer Sequencing (recommended for this refactor)

Because phases are strictly sequential, this is best executed by one developer in order, committing after each phase. Parallelism exists only within a phase (different files), useful if reviewing as you go.

---

## Notes

- **Class names are kept** in this refactor (only file/module paths move) to keep diffs reviewable as pure moves (research D1/D2). The frozen contract does not reference these classes by string.
- **Celery task `name=` strings and queues are frozen** — only the import path the worker uses to find task functions changes (contract §2).
- **Alembic migrations are historical and untouched** — no revision hashes, `version_locations`, or `env.py` metadata target changes (contract §5).
- **Test assertion changes are forbidden**; test import-line changes are allowed and expected.
- Commit after each phase (one revertible unit per FR-011).
- Avoid: splitting a file by line count only (split by responsibility), renaming classes mid-refactor (defer), touching the frozen contract surfaces.
