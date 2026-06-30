# Phase 0: Research — Architecture Refactor (003)

**Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

This resolves every open design decision for the refactor. Each decision lists **Decision / Rationale / Alternatives**. No NEEDS CLARIFICATION markers remain (the `/speckit-clarify` session resolved the 5 user-facing choices; this document resolves the technical execution choices).

---

## D1 — How to relocate `controllers/` (application services)

**Decision**: Merge `controllers/` into the **existing** `services/` package. `BaseController.py` → `services/base.py`; `*Controller.py` → `*_service.py` (class names stay stable per FR-001 — only file names move). The RAG pair (`NLPController` + `RAGService`) goes into a `services/rag/` sub-package.

**Rationale**: The codebase already has `services/` (`RAGService.py`, `FieldRegistry.py`). The `.NET-equivalent` doc and `BaseController`'s own docstring both state these are services, not controllers. Creating a third package would fragment application logic across `controllers/` + `services/`. Merging is one move, not two.

**Class-name policy**: Class identifiers (`NLPController`, `ProjectController`, `DataController`, `ProcessController`, `BaseController`) are **internal** and MAY be renamed, but per Q2 the safer default is to **keep class names** in this refactor (only file/module paths change) to minimize blast radius and keep the diff a pure move. The spec permits renaming classes; the plan defers class renaming to a later cleanup unless a name actively conflicts (none do today).

**Alternatives rejected**:
- *Rename folder to `application/`*: rejected — `services/` already exists and matches the constitution's "Application — use cases and orchestration (`controllers/`, `services/`)" wording.
- *Rename classes too (`NLPController`→`RagOrchestrator`)*: rejected for this refactor — increases risk for no behavioral gain; deferred.

---

## D2 — How to relocate `models/` (mixed entities + repositories)

**Decision**: **Split** `models/`. Repository files (`ProjectModel.py`, `ChunkModel.py`, `AssetModel.py`, `ChatMessageModel.py`, `BaseDataModel.py`) move to a new `repositories/` package (renamed `*_repository.py`, e.g. `project_repository.py`). `models/` keeps `db_schemes/` + `enums/` as the pure domain-entity layer.

**Rationale**: Audit (`ls src/models/`) shows `models/` contains 5 repository files **and** the entity subpackages `db_schemes/` (SQLAlchemy ORM) + `enums/`. A blanket `models/`→`repositories/` rename would put ORM entities and Alembic migrations under a "repositories" namespace — a worse lie than today, and it would require changing Alembic's `version_locations` and the migration env's target metadata path, risking the frozen migration contract (FR-001).

**Class-name policy**: Repository classes (`ProjectModel`, `ChunkModel`, …) MAY be renamed to `*Repository`, but again the plan defaults to **keeping class names** and only moving/renaming files, to keep the diff a pure move. The frozen contract does not reference these class names by string.

**Alternatives rejected**:
- *Rename whole `models/`→`repositories/`*: rejected (entity misplacement + Alembic risk, above).
- *Leave `models/` as-is*: rejected — fails FR-004 ("models/ holds data-access repositories, not entities") and User Story 1.

---

## D3 — How to split the oversized files (≤400 SLOC)

SLOC estimates (non-blank, non-comment; docstrings counted loosely — implementer will verify with a counter at P2):

| File | ~SLOC | Split plan |
|------|-------|------------|
| `NLPController.py` | ~547 | → `services/rag/`: `embedding.py` (`_embed_query*`), `search.py` (`_vector_search`, `_fetch_dense_and_sparse_candidates`, `search_vector_db_collection`), `fusion.py` (`_run_expansion_and_merge`), `enrichment.py` (`enrich_retrieved_documents`, `_expand_structural_context`, `_append_chunk_if_new`), `rag_service.py` (collection mgmt: `index_into_vector_db`, `reset_vector_db_collection`, `get_vector_db_collection_info`, `build_profile_for_project`). Each <400 SLOC. |
| `RAGService.py` | ~299 | Already <400; stays as `services/rag/answer_service.py`. Prompt-assembly helper `_document_text_for_prompt` extracted to `prompt.py` only if `answer_service.py` would exceed budget after merge — otherwise inline. |
| `PGVectorProvider.py` | ~483 | → `stores/vectordb/providers/pgvector/`: `connection.py` (`connect`, extension setup), `schema.py` (table/index/collection DDL + identifier allow-list `_validate_identifier` preserved **verbatim**), `search.py` (dense + sparse search queries), `provider.py` (facade class implementing `VectorDBInterface`, delegates to the above). |
| `core/retrieval/engine.py` | ~443 | → `core/retrieval/`: `fusion.py` (`hybrid_rrf`, `merge_retrieved_documents`, `deduplicate_retrieved_documents`), `rerank.py` (`rerank_retrieved_documents`, `sort_documents_for_prompt`), `focus.py` (continuation + detail/comparison/exhaustive heuristics + `_source_key`). `__init__.py` re-exports everything so `from core.retrieval.engine import X` AND `from core.retrieval import X` both work during migration. |
| `core/structural/engine.py` | ~325 | Already <400 SLOC; stays as one file. Re-exported via `core/structural/__init__.py`. |
| `FieldRegistry.py` | ~371 | Already <400 SLOC; unchanged location. |

**Rationale**: Each split is along pre-existing responsibility seams already documented in each file's own docstrings/section comments — no logic is invented, only relocated. Provider facade + `__init__` re-exports keep external import paths stable.

**Alternatives rejected**:
- *Split by line count only (mechanical)*: rejected — would break cohesive functions across files; splits follow responsibility boundaries.
- *Rewrite algorithms while splitting*: rejected — violates FR-001 (behavior-preserving). Splits are pure moves.

---

## D4 — Shim removal (Q3 = Option C)

**Decision**: Delete `utils/retrieval.py` and `utils/structural_split.py`. Migrate their 5 callers to import from `core.retrieval.engine` / `core.structural.engine` directly (after D3, also `core.retrieval` / `core.structural` work). Callers (from grep): `services/RAGService.py`, `controllers/NLPController.py`, `controllers/ProcessController.py`, plus tests.

**Rationale**: Option C (decided in clarify) fully removes duplication and matches User Story 4. With D3's `__init__` re-exports, migration is a one-line import change per caller.

**Alternatives rejected**:
- *Keep shims with DeprecationWarning*: rejected — leaves duplicate import paths, contradicts "remove duplicated logic".
- *Migrate callers but keep shims*: rejected — same reason.

---

## D5 — Misplaced domain code & duplicate config

**Decision**:
- `utils/pharmacy_compat.py` → `fields/pharmacy/compat.py` (domain code belongs with its field pack; `utils/` keeps only cross-cutting helpers). Update its callers.
- `src/flowerconfig.py` is the single source of truth for Flower; `docker/flowerconfig.py` is a duplicate. Keep `src/flowerconfig.py`, point `docker/docker-compose.yml` at it (verify the current reference path), delete the `docker/` copy.

**Rationale**: FR-005 (relocate misplaced files) + FR-006 (single source of truth). Flower config in two roots is a classic deploy-time divergence bug.

**Alternatives rejected**:
- *Keep `pharmacy_compat.py` in `utils/`*: rejected — `utils/` is for cross-cutting code; pharmacy is one domain among several.
- *Keep both flowerconfig copies*: rejected — divergent config risk.

---

## D6 — Frozen-contract guard (FR-001 / FR-009)

**Decision**: Add `tests/contract/` with a snapshot-style guard that captures, before refactor: (a) the FastAPI route table (paths, methods, prefix, tags), (b) Celery task `name=` strings + `task_routes` keys, (c) `Settings` env-var names, (d) Prometheus metric/label names from `utils/metrics.py`. After each phase, re-run and assert the snapshot is unchanged.

**Rationale**: FR-001 is the hard constraint; a programmatic guard is stronger than manual review. The snapshot is generated from the **pre-refactor** `main` branch state.

**Alternatives rejected**:
- *Manual API diff review*: rejected — error-prone for a refactor this size.

---

## D7 — Sequencing & revert safety (FR-011 / Q4 = phased)

**Decision**: Phase order P1 (renames/moves) → P2 (splits) → P3 (dedup) → P4 (docs + contract guard). Reason: renames must land before splits (so splits operate on final paths), and shim deletion (P3) must follow the `core/` re-export stability from P2.

**Rationale**: Each phase ends green. If a phase breaks the contract, revert that phase only — earlier phases stand.

**Alternatives rejected**:
- *Single big-bang commit*: rejected (Q4 = phased) — unreviewable, unrevertable.
- *Split before rename*: rejected — would split files at old paths, then move the pieces (double churn).
