# Feature Specification: Architecture Refactor (behavior-preserving)

**Feature Branch**: `003-architecture-refactor`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Refactor project architecture without changing behavior. Audit entire codebase. Rename misleading files and classes. Split oversized files (>400 LOC). Move files into correct packages. Enforce SRP. Remove duplicated logic. Improve folder structure. Keep all public APIs and endpoints unchanged."

**Depends on**: `002-field-registry` (introduces `core/`, `fields/`, `services/FieldRegistry` that this refactor tidies up; no behavior change).

**Supersedes**: None.

## Clarifications

### Session 2026-06-30

- Q: Target package naming strategy for the `controllers/` (services) and `models/` (repositories) layers? → A: Option A — full rename in lockstep: `controllers/`→`services/` (repository classes → `repositories/`), updating all imports, tests, and `ARCHITECTURE.md` together.
- Q: How to handle internal class renames referenced via string (Celery task paths, SQLAlchemy/Alembic entry points)? → A: Internal class/file names MAY change; the Celery task **names** (the `name=` strings Celery calls and `task_routes` keys) and SQLAlchemy/Alembic entry-point identifiers MUST stay byte-stable so task routing and migrations are unaffected.
- Q: Single refactor PR/commit or sequenced phases? → A: Sequenced phases (one phase per concern: renames → splits → moves → dedup), each independently testable and revertible.
- Q: How is the "400 LOC" limit counted? → A: SLOC = executable statements + declarations only. Excluded: blank lines, line/block comments, XML doc markers, and docstrings.
- Q: Aggressiveness of deprecated shim removal (`utils/retrieval.py`, `utils/structural_split.py`)? → A: Option C — migrate all callers to import directly from `core/retrieval.engine` and `core/structural.engine`, then delete both shims entirely, all within this feature's phases (no lingering re-exports).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Developer Finds Code Where They Expect It (Priority: P1)

A developer joining the project opens the source tree and immediately understands where each responsibility lives. Directories are named after what they do (presentation, application logic, data access, entities, infrastructure), and a class name matches its file name and its single responsibility. Nothing the developer sees contradicts the project's architecture guide.

**Why this priority**: The whole point of the refactor is comprehension. If names and locations still mislead, the refactor failed.

**Independent Test**: A reviewer who has never seen the code is asked "where is the HTTP handler for the RAG answer endpoint?" and "where does the actual RAG orchestration live?" — they answer correctly from directory and file names alone, without opening the files.

**Acceptance Scenarios**:

1. **Given** the source tree, **When** a reviewer reads directory names, **Then** the presentation layer (HTTP) and the application-logic layer are in folders whose names say "HTTP/routes" and "services", not "controllers".
2. **Given** any Python module, **When** its primary class is inspected, **Then** the class name, the file name, and the folder name all describe one coherent responsibility.
3. **Given** the existing `src/ARCHITECTURE.md` map, **When** a developer follows it, **Then** every listed file exists at the documented location (the doc is updated wherever moves happen).

---

### User Story 2 - Maintainer Edits One Responsibility in One File (Priority: P1)

A maintainer needs to change a single concern (e.g., how RRF fusion ranks documents, or how a chunk is enriched with neighbor context). They open exactly one small file and make the change. The file has one reason to change (SRP) and is under the size limit, so navigation and review are fast. They do not have to touch a 600-line "god" module that mixes five responsibilities.

**Why this priority**: SRP and the 400-LOC limit are the measurable core of the refactor.

**Independent Test**: Pick any current file over 400 LOC; after the refactor each split piece is under 400 LOC and addresses a single responsibility. `git log --stat` shows the original logic was only moved/split, not rewritten.

**Acceptance Scenarios**:

1. **Given** `NLPController.py` (643 LOC, mixes embedding, vector search, fusion, structural enrichment, orchestration), **When** the refactor lands, **Then** it is split into focused modules each under 400 LOC and each with one stated responsibility.
2. **Given** `PGVectorProvider.py` (609 LOC, mixes connection, DDL, search, filter parsing), **When** split, **Then** each resulting module is under 400 LOC.
3. **Given** `core/retrieval/engine.py` (574 LOC, mixes fusion, merge, dedupe, rerank, continuation, focus heuristics), **When** split, **Then** each algorithm family lives in its own focused module under 400 LOC.
4. **Given** `FieldRegistry.py` (460 LOC) and `core/structural/engine.py` (403 LOC), **When** the 400-LOC rule is applied, **Then** they are either under 400 LOC or split along clear responsibility lines.

---

### User Story 3 - Operator Runs the App and Sees Zero Behavior Change (Priority: P1)

After the refactor is deployed, every API endpoint, request/response shape, Celery task, CLI behavior, and observable metric behaves identically to before. The refactor is invisible to anyone calling the system. Existing tests pass unchanged (only import paths move when an import points at a renamed module).

**Why this priority**: "Without changing behavior" is the hard constraint that makes this a refactor, not a rewrite.

**Independent Test**: Run the full test suite and the documented API contract checks before and after; the same assertions pass. No public endpoint, route, request schema, response field, Celery task name, or env-var name changes.

**Acceptance Scenarios**:

1. **Given** the API surface (`/api/v1/projects`, `/api/v1/data`, `/api/v1/nlp/*`), **When** the refactor lands, **Then** every path, method, request body, and response body is byte-for-byte equivalent.
2. **Given** the Celery task names and queues, **When** a worker starts, **Then** it discovers and runs the same tasks on the same queues with the same routing.
3. **Given** the existing unit and integration test suite, **When** it runs on the refactored code, **Then** all previously-passing tests still pass (import-line fixes in tests are allowed; assertion changes are not).
4. **Given** Prometheus metric names and labels, **When** observed, **Then** they are unchanged.

---

### User Story 4 - No Two Places Implement the Same Logic (Priority: P2)

A maintainer searching for "how is RRF computed" or "where is the Celery app configured" finds exactly one definition. Deprecated re-export shims are removed (or their removal is tracked), and stray duplicate files (e.g., the same config in two roots) are consolidated to a single source of truth.

**Why this priority**: Duplication breeds divergence bugs; removing it is a stated goal.

**Independent Test**: `grep` for a given function/constant returns exactly one defining occurrence in the source tree (re-exports, if kept temporarily, are clearly marked as deprecated).

**Acceptance Scenarios**:

1. **Given** `utils/retrieval.py` and `utils/structural_split.py` are deprecated re-export shims still imported by 5 call sites, **When** the refactor completes, **Then** callers import from the real modules and the shims are removed (or marked with an explicit removal date).
2. **Given** `src/flowerconfig.py` duplicates `docker/flowerconfig.py`, **When** consolidated, **Then** there is exactly one Flower config source referenced by `docker-compose.yml`.
3. **Given** domain-specific code (e.g., `utils/pharmacy_compat.py`) sitting in the cross-cutting `utils/` package, **When** relocated, **Then** it lives under the domain/feature package it belongs to, and `utils/` contains only genuinely cross-cutting helpers.

---

### User Story 5 - New Capability Has a Clear Home (Priority: P3)

A developer adding a new feature can look at the folder structure and know exactly where new code goes (which package for a route, which for application logic, which for a repository, which for an entity, which for an infrastructure provider). The structure enforces the layering rules already written in the constitution.

**Why this priority**: Structure should guide future work, not just tidy the past.

**Independent Test**: The maintainer places a hypothetical new "reporting" feature's files; a reviewer confirms each file landed in the constitutionally-correct package with no inward dependency from infrastructure to core.

**Acceptance Scenarios**:

1. **Given** the folder map documented in `src/ARCHITECTURE.md`, **When** a new feature is added, **Then** its route, service, repository, entity, and provider files each land in the package the map prescribes.
2. **Given** the Clean Architecture rule "inner layers must not import outer layers", **When** imports are checked, **Then** no file in `core/`, `models/db_schemes/`, or domain packs imports from `routes/`, `controllers/`-as-services, or `stores/`.

---

### Edge Cases

- What happens when renaming a class that is referenced via string (Celery task paths, SQLAlchemy entry points, Alembic)? → Those string references must be updated in lockstep; task names MUST NOT change.
- What happens when a file is renamed but an external tool (Docker entrypoint, Flower config path, Alembic `main.py`) references the old path? → Update the reference or keep a thin alias with a deprecation note.
- What happens when splitting a file breaks an import that the test suite relies on? → Update the import; tests may change import lines but not assertions.
- What happens when two oversized files share private helpers? → Extract the shared helper into a small focused module rather than duplicating it in both splits.
- What happens to backward-compat re-exports the team is not ready to drop? → Keep them with a clear `DEPRECATED` header and a removal target; do not silently leave them.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be delivered as a behavior-preserving refactor: every public HTTP endpoint, request/response schema, Celery task **name** (the `name=` string Celery calls and the `task_routes` keys) and queue, CLI entrypoint, env-var name, and Prometheus metric name/label MUST remain identical to the pre-refactor system. Internal class and file names MAY change; string identifiers that Celery or SQLAlchemy/Alembic resolve at runtime MUST stay stable so task routing and migrations are unaffected.
- **FR-002**: System MUST have no source file exceeding 400 **SLOC** (executable statements + declarations; blank lines, comments, XML doc markers, and docstrings are excluded). Every file currently over 400 SLOC (`NLPController.py`, `PGVectorProvider.py`, `core/retrieval/engine.py`, `FieldRegistry.py`, `core/structural/engine.py`, and any others found during the audit) MUST be split along clear responsibility boundaries, each resulting piece under the limit.
- **FR-003**: Every module and its primary class MUST satisfy a Single Responsibility. Specifically, the RAG answer path (currently `NLPController` + `RAGService`) MUST be decomposed so that embedding, vector search, fusion/expansion, structural enrichment, reranking, prompt building, and generation are each isolated concerns (they may collaborate, but none owns the others' logic).
- **FR-004**: Files and classes MUST be renamed so that the name describes the responsibility and matches the .NET-equivalent role described in `src/ARCHITECTURE.md`. Specifically, the layer currently called `controllers/` (which holds application services, not HTTP handlers) MUST be renamed to `services/`, and the layer currently called `models/` (which holds data-access repositories, while true entities live in `models/db_schemes/`) MUST be renamed to `repositories/`. The rename MUST be done in lockstep: all imports, test import lines, `src/ARCHITECTURE.md`, and any path references in `docker/` and `docker-compose.yml` updated together so documented paths match reality.
- **FR-005**: System MUST relocate misplaced files to the package matching their responsibility: domain-specific code MUST NOT live in the cross-cutting `utils/` package; duplicated configuration (e.g., Flower config present in both `src/` and `docker/`) MUST be consolidated to a single source of truth referenced consistently by deployment files.
- **FR-006**: System MUST remove duplicated logic: deprecated re-export shims (`utils/retrieval.py`, `utils/structural_split.py`) MUST be deleted, with all callers migrated to import directly from `core/retrieval.engine` and `core/structural.engine` within this feature's phases. No lingering re-exports, and no two definitions of the same algorithm/constant may coexist.
- **FR-007**: The folder structure MUST enforce constitution-aligned Clean Architecture layering: presentation (`routes/`), application logic, data access, domain/entities (`models/db_schemes/`), and infrastructure (`stores/`, `utils/`, Celery tasks) MUST be in distinct, correctly-named packages. Inner layers MUST NOT import from outer layers.
- **FR-008**: `src/ARCHITECTURE.md` and any path references in `docker/`, Alembic config, and `docker-compose.yml` MUST be updated in lockstep with every file move/rename so that documented paths match reality.
- **FR-009**: The refactor MUST be validated by the full existing test suite (unit + integration) passing unchanged in its assertions, plus a regression check that confirms the API contract (paths, methods, schemas, responses) and Celery task registry are unchanged before and after.
- **FR-010**: Field-registry work from `002-field-registry` (`core/`, `fields/`, `services/FieldRegistry.py`) MUST remain functional and correctly placed; this refactor tidies and aligns it with the new structure but MUST NOT alter its behavior or its public profile API.
- **FR-011**: The refactor MUST be delivered in sequenced phases, one phase per concern (renames → oversized-file splits → file moves → duplication removal). Each phase MUST be independently runnable, testable, and revertible, and MUST leave the system green (full suite passing) after every phase.

### Key Entities

- **Module/Responsibility unit**: the atomic thing being moved/renamed/split; each must end up with one reason to change.
- **Public API contract**: the frozen set of endpoints, schemas, task names, env vars, and metrics that define "behavior unchanged".
- **Backward-compat shim**: a re-export kept temporarily for migration; must carry a removal target.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Refactor MUST respect Clean Architecture boundaries (constitution Principle I); moves and renames MUST NOT introduce inward imports from infrastructure to core/domain.
- **NFR-002**: Refactor MUST preserve async-first and typed public APIs (Principle IV); splitting files MUST NOT downgrade async signatures or drop type hints.
- **NFR-003**: Pluggable provider wiring (LLM, embedding, vector DB, reranker factories — Principle V) MUST remain in composition roots (`main.py`, `celery_runtime.py`, factories); splitting providers MUST NOT move provider selection into services or routes.
- **NFR-004**: RAG answer paths MUST continue to return source citations and use versioned prompts (Principle VI) — refactor MUST NOT drop citation/prompt-assembly code.
- **NFR-005**: Unit and integration tests MUST cover the same behavior before and after (Principle VII); if a split changes an internal boundary, a test must still exercise that behavior.
- **NFR-006**: Structured logging correlation ids at service boundaries (Principle VIII) MUST survive the split intact.
- **NFR-007**: Refactor MUST NOT introduce secrets into source, weaken SQL parameterization, or relax upload validation (Principle IX). The pgvector identifier allow-list logic MUST be preserved verbatim through any split.
- **NFR-008**: Refactor MUST NOT move long-running work out of Celery workers or into request handlers (Principle X).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of source files are at or below 400 SLOC (executable + declarations; blanks/comments/docstrings excluded), verifiable by an SLOC counter over the tree.
- **SC-002**: 0 files over 400 SLOC remain; each previously-oversized file is split into named, single-responsibility pieces.
- **SC-003**: Every directory and primary class name matches its responsibility; specifically, the `controllers/`-as-services and `models/`-as-repositories naming conflicts are resolved and reflected in `src/ARCHITECTURE.md`.
- **SC-004**: Every duplicate definition is consolidated to a single source of truth; deprecated shims are either removed or carry an explicit removal date.
- **SC-005**: 100% of the previously-passing test suite passes with no assertion changes, and an API/Celery contract comparison shows zero differences before vs. after.
- **SC-006**: A reviewer unfamiliar with the code correctly identifies the location of (a) HTTP handlers, (b) RAG orchestration, (c) data access, (d) DB entities, and (e) provider wiring using only names and folder structure.
- **SC-007**: No file in an inner layer (`core/`, domain packs, `db_schemes/`) imports from an outer layer (`routes/`, application services, `stores/`).

## Assumptions

- "Behavior unchanged" is defined by the frozen contract in FR-001: endpoints, schemas, Celery task **names**/queues, CLI entrypoints, env vars, and metric names/labels. Internal class/file/import names are explicitly in scope to change; Celery/SQLAlchemy runtime-resolved string identifiers are NOT (see FR-001).
- "400 LOC" is measured as **SLOC** = executable statements + declarations. Blank lines, line comments (`#`), block comments, XML doc markers, and docstrings are excluded from the count (see FR-002).
- The target folder names are decided: `controllers/`→`services/` and `models/`→`repositories/` (see FR-004). The plan will resolve exact internal class names and any sub-package structure.
- The team is willing to update import lines in the existing test suite (allowed) but not assertions (not allowed).
- Backward-compat re-exports are NOT retained: the deprecated `utils/retrieval.py` and `utils/structural_split.py` shims are deleted and all callers migrated to `core/` within this feature (see FR-006).
- Domain packs under `fields/` (pharmacy, legal, generic) are configuration, not code to split; they are relocated only if their path conflicts with the new structure, and their YAML content is unchanged.
- Frontend assets under `src/frontend/` are out of scope for splitting/renaming; only their mount path in `main.py` must remain stable.
