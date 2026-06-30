# Feature Specification: Field Registry Architecture

**Feature Branch**: `002-field-registry`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description: "معمارية Field Registry عامة قبل التنفيذ: مجلد fields/ لكل مجال (Pharmacy, Legal, …) يحتوي retrieval و structural_split و chunk_metadata و chunking و prompts. الكود الأساسي واحد؛ الفرق بين المجالات في الـ configs فقط. ربط المشروع بالمجال عبر جدول في DB للهوية والـ overrides."

**Depends on**: None (foundational).

**Supersedes**: `001-pharmacy-query-enhancement` (archived; pharmacy content merged below as Phase D).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Platform Admin Selects Field for a Project (Priority: P1)

A platform administrator creates a new project and assigns it a professional field (e.g., Pharmacy, Legal, Generic). The system automatically applies the correct ingestion rules, retrieval behavior, and default prompts for that field without code changes or redeployment.

**Why this priority**: Field selection is the entry point for all domain-specific behavior.

**Independent Test**: Create two projects with different fields; upload the same PDF to both; verify chunking and answer style differ according to each field's profile.

**Acceptance Scenarios**:

1. **Given** a new project with `domain_key = pharmacy`, **When** create completes, **Then** `projects.config_json` equals the parsed content of `fields/pharmacy/project.defaults.yaml` (plus any request overrides).
2. **Given** a project with `domain_key = legal`, **When** a user asks about "مادة 12", **Then** structural article-aware retrieval is applied (not pharmacy row logic).
3. **Given** no field assigned, **When** the project is used, **Then** the `generic` field pack applies safe defaults.

---

### User Story 2 - Field Pack Author Maintains Domain Configs (Priority: P1)

A maintainer adds or updates a field pack under `fields/{domain}/` (retrieval patterns, chunking strategy, prompts) in version control. Changes deploy with the application and apply to all projects using that field, unless overridden at project level.

**Why this priority**: Separates stable domain knowledge from per-project customization.

**Independent Test**: Modify a pattern in `fields/pharmacy/retrieval.yaml`; run unit tests for pharmacy intent detection; no changes required in `NLPController` body.

**Acceptance Scenarios**:

1. **Given** a new retrieval pattern in `fields/legal/retrieval.yaml`, **When** tests run, **Then** legal exhaustive-list queries match without editing core pipeline code.
2. **Given** a field pack with invalid YAML, **When** the app starts, **Then** startup fails fast with a clear validation error (or falls back to generic with logged warning — see Assumptions).

---

### User Story 3 - Project-Level Overrides Without Forking Code (Priority: P2)

A pharmacy customer uses different Excel file names than the defaults. The admin overrides file roles and chunk size in project config while keeping `domain_key = pharmacy`.

**Why this priority**: Real deployments need per-customer file naming without new code branches.

**Independent Test**: Two pharmacy projects with different `file_roles` in DB both use the same pharmacy field pack code.

**Acceptance Scenarios**:

1. **Given** project A overrides `catalog` file to `MY_DRUGS.xlsx`, **When** retrieval targets catalog source, **Then** only that file is preferred for catalog queries.
2. **Given** project B uses default pharmacy file roles, **When** configured, **Then** standard `FINALMEDICIN.xlsx` mapping applies.

---

### User Story 4 - Developer Adds a New Field (Priority: P2)

A developer adds `fields/medical/` by copying the generic template, filling domain YAML files, and registering in `fields/registry.yaml`. No changes to `RAGService` or `NLPController` orchestration logic are required.

**Why this priority**: Proves the "one engine, many configs" goal.

**Independent Test**: Register a stub `medical` field; assign to a test project; verify loader resolves profile.

**Acceptance Scenarios**:

1. **Given** `medical` registered in `registry.yaml`, **When** a project uses `domain_key = medical`, **Then** the medical profile loads all configured modules.
2. **Given** an unknown `domain_key`, **When** a project references it, **Then** system falls back to `generic` and logs a warning.

---

### Edge Cases

- Project changes field after documents are indexed (requires re-index warning).
- Field pack updated in deploy while projects have DB overrides (merge: DB wins on conflicts).
- Mixed-language queries (Arabic/English) — each field pack declares supported languages.
- Field pack missing optional module (e.g., no `structural_split.yaml`) — use generic module for that slice.
- `001-pharmacy-query-enhancement` is superseded; all pharmacy work ships under Phase D below.

---

## Phase D — Pharmacy field pack (`fields/pharmacy/`)

*Merged from archived `001-pharmacy-query-enhancement`. Implements after registry Phases A–C.*

Production failures to fix: incomplete exhaustive lists (e.g. muscle relaxants 1 of 7+), inconsistent interaction answers, prescription cross-check gaps, follow-up questions losing drug context.

### Pharmacy User Story P1 — Exhaustive drug class listing

A pharmacist asks: "كل الادوية المصنفة كباسط للعضلات". The system returns **every** matching drug in indexed spreadsheets, not a partial sample.

**Acceptance**:

1. **Given** indexed `FINALMEDICIN.xlsx` with N muscle-relaxant rows, **When** the user asks in Arabic, **Then** all N drugs appear with Source Coverage.
2. **Given** the same query twice, **When** data unchanged, **Then** identical drug set and count.
3. **Given** no matches, **Then** clearly state information is unavailable.

### Pharmacy User Story P1 — Complete interaction lookup

A pharmacist asks: "عايز كل الادوية المتعارضة مع cordarone". All documented interactions from indexed files must appear.

**Acceptance**:

1. All M interactions for amiodarone/Cordarone from source files appear in the answer.
2. Conflicting sources → identify discrepancies without favoring one.
3. Follow-up "عايزهم كلهم مهما كان عددهم" → does not narrow; expands retrieval if needed.

### Pharmacy User Story P2 — Prescription cross-check

User pastes a multi-drug prescription and asks which drugs interact with each other.

**Acceptance**: Parse all drug names; report only documented pairwise interactions; mark unknown drugs as unavailable.

### Pharmacy User Story P2 — Bilingual pharmacist prompt

Project uses custom `prompt_ar` / `prompt_en` (seeded from `fields/pharmacy/prompts/` on create, stored in `project_prompts`). Output: # الملخص / # التفاصيل / # التحذيرات / # تغطية المصدر. No start/stop/change medication advice.

### Pharmacy User Story P3 — Follow-up context

"dimra استخدامات" then "الجرعة الخاصة به" without repeating the drug name → retrieval resolves drug from chat history.

### Pharmacy functional requirements

- **PH-FR-001**: Classify pharmacy intents (exhaustive_list, drug_detail, interaction_lookup, prescription_check, comparison) via `fields/pharmacy/retrieval.yaml` + optional LLM rewrite (`core/query_understanding.py`).
- **PH-FR-002**: Detect Arabic/English exhaustive patterns ("كل الادوية", "عايزهم كلهم", "all drugs") → exhaustive retrieval mode.
- **PH-FR-003**: Row-aware chunking for `.xlsx` via `by_extension` in `project.defaults.yaml` / field pack.
- **PH-FR-004**: Multi-query retrieval (original + rewritten + expansions), merge before rerank.
- **PH-FR-005**: Prescription parser for multi-drug input (rule-based + optional LLM fallback).
- **PH-FR-006**: Follow-up entity carry-over from chat history into query rewrite.
- **PH-FR-007**: Enumerate all items from all retrieved docs for exhaustive queries; no grounding violations.
- **PH-FR-008**: Structured API citations alongside human-readable Sources.

### Pharmacy success criteria

- **PH-SC-001**: Exhaustive class queries ≥95% row recall vs source (muscle relaxants benchmark).
- **PH-SC-002**: Repeated identical interaction queries ≥99% same count.
- **PH-SC-003**: 5-drug prescription benchmark reports all documented pairwise hits.
- **PH-SC-004**: Query rewrite adds ≤2s p95 latency.
- **PH-SC-005**: 100% benchmark answers include Source Coverage + safety disclaimers.

### Pharmacy field pack files

```text
fields/pharmacy/
├── project.defaults.yaml    # copied → projects.config_json on create
├── retrieval.yaml           # intents, patterns, exhaustive rules
├── query_rewrite.yaml       # LLM rewrite prompt template (optional)
├── chunking.yaml            # by_extension (.xlsx: row, …)
├── chunk_metadata.yaml
└── prompts/
    ├── system_ar.txt
    └── system_en.txt
```

---

### Functional Requirements

- **FR-001**: System MUST provide a `fields/` directory structure where each domain (pharmacy, legal, generic, …) contains separate config modules: `chunking`, `retrieval`, `structural_split`, `chunk_metadata`, `file_roles`, `prompts`.
- **FR-002**: System MUST expose a `FieldRegistry` that loads and validates field packs at startup (or first use) from `fields/registry.yaml`.
- **FR-003**: System MUST keep a single shared RAG pipeline (`core`) that executes retrieval, chunking, and generation using the active field profile — no duplicated pipeline per domain.
- **FR-004**: Each project MUST store exactly one `domain_key` as an enum column on the `projects` table (default `generic`).
- **FR-005**: On project creation, system MUST read `fields/{domain_key}/project.defaults.yaml`, merge optional request `config_json`, validate, and **persist the result** to `projects.config_json`. Runtime MUST use the DB snapshot, not re-read the YAML per request.
- **FR-006**: Existing `project_prompts` MUST remain the store for long bilingual system prompts; field packs provide defaults, projects may override.
- **FR-007**: Core Python files (`retrieval.py`, `structural_split.py`, `ProcessController`, `RAGService`, `NLPController`) MUST be refactored to delegate domain-specific rules to field profiles (measurable reduction in domain-specific code in core).
- **FR-008**: Adding a new field MUST require only new files under `fields/{name}/` plus registry entry — not edits to orchestration classes.
- **FR-009**: System MUST merge field defaults with project overrides using documented precedence: `project DB override` > `project_prompts` > `field pack default` > `generic fallback`.
- **FR-010**: Migration path MUST preserve behavior for existing projects (default `domain_key = generic` until admin assigns a field).

### Key Entities

- **FieldPack**: Registered domain profile (pharmacy, legal, generic) loaded from `fields/{key}/`.
- **FieldModule**: Named slice of a pack (retrieval, structural_split, chunking, chunk_metadata, file_roles, prompts).
- **Project** (extended): `domain_key` enum + `config_json` jsonb on `projects`; `project_prompts` for prompt text.
- **FieldProfile**: Runtime merged view (pack + project overrides) passed to core pipeline.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Clean Architecture — `core/` orchestration; `fields/` as configuration boundary; loaders in `services/` or `helpers/`.
- **NFR-002**: Async + typed public APIs for profile loading and merge.
- **NFR-003**: No provider-specific imports in field packs (YAML/text only for configs).
- **NFR-004**: Source citations and prompt versioning preserved.
- **NFR-005**: Unit tests per field pack module; integration tests for profile merge and pipeline delegation.
- **NFR-006**: Field pack load failures logged with `domain_key`; metrics for active field per request.
- **NFR-008**: No secrets in field pack files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Adding a new field requires changes in at most `fields/{new}/` + `registry.yaml` + tests — zero edits to `RAGService` / `NLPController` orchestration (verified by checklist in plan).
- **SC-002**: Domain-specific line count in `utils/retrieval.py` and `utils/structural_split.py` reduced by ≥60% after refactor (logic moved to field packs).
- **SC-003**: Two projects on different fields demonstrate different chunking/retrieval for the same uploaded file type without code fork.
- **SC-004**: 100% of existing generic/legal regression tests pass with `domain_key = generic` after migration.
- **SC-005**: Pharmacy Phase D (`fields/pharmacy/`) passes PH-SC-001 through PH-SC-005 benchmarks.

## Assumptions

- Field pack format is YAML for structured rules and `.txt` for prompts (validated by schema).
- Invalid field pack at startup: fail fast in production, optional warn+generic in development.
- `001-pharmacy-query-enhancement` is superseded; content lives in Phase D above.
- Admin UI for field selection is out of scope v1 (API/DB only); frontend can follow later.
- `fields/` directory lives at repository root or `src/fields/` — exact path decided in plan (recommend `src/fields/` for Python imports).
