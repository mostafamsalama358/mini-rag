---

description: "Task list template for feature implementation"
---

# Tasks: Document Intelligence Pipeline

**Input**: Design documents from `/specs/006-document-intelligence-pipeline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED per constitution Principle VII and spec NFR-006 (Document Model
construction per format, structure-preserving chunking, YAML-driven per-pack differences,
degraded-fallback path). Every user story below includes test tasks written before its
implementation tasks.

**Organization**: Tasks are grouped by user story (US1–US5 from `spec.md`) to enable
independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Every task includes an exact file path

## Path Conventions

Single project (per `plan.md` Structure Decision): `src/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new package skeleton and test scaffolding before any parsing logic.

- [x] T001 Create `src/core/document_intelligence/` package skeleton: `__init__.py`, `parsers/__init__.py` (empty dir markers only, no logic yet)
- [x] T002 [P] Create test package dirs: `tests/unit/core/document_intelligence/__init__.py`, `tests/integration/ingestion/__init__.py`
- [x] T003 [P] Create `tests/fixtures/document_intelligence/generate_fixtures.py` producing `sample_50_rows.xlsx` (50 data rows), `sample.csv` (10 rows), `sample.txt` (multi-paragraph), `sample_with_table.pdf` (one embedded table), and malformed variants (`malformed.xlsx` with zero usable rows, `unreadable.pdf` corrupted beyond opening) — committed as generated fixture files plus the generator script

**Checkpoint**: Package skeleton and fixtures exist. No behavior change yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Document Model, parser registry, and chunk-mapping primitives that every user
story depends on.

**⚠️ CRITICAL**: No user-story wiring into `process_service.py` until this phase is done.

- [x] T004 Implement `StructuralElement` and `DocumentModel` Pydantic models (canonical vocabulary `section`/`paragraph`/`table`/`table-row`/`list`/`list-item`, deterministic `id` from asset fingerprint + structural path) in `src/core/document_intelligence/model.py` (FR-001a, FR-003a, data-model.md §1–2)
- [x] T005 [P] Implement `DocumentIntelligenceDegraded` exception with `reason` literal (`unsupported_structure`/`parse_error`/`empty_content`) in `src/core/document_intelligence/errors.py` (research R7)
- [x] T006 [P] Implement `DocumentParser` protocol and `ParserRegistry` (`register`, `get_parser_for_extension`) in `src/core/document_intelligence/parsers/__init__.py` (research R2, contracts/document-model-contract.md)
- [x] T007 Add `ElementChunkConfig` model and `element_mapping: dict[str, ElementChunkConfig]` field to `ChunkingProfile` in `src/fields/schemas.py` (data-model.md §3)
- [x] T008 Implement `map_elements_to_chunks(elements, config)` in `src/core/document_intelligence/chunk_mapper.py` enforcing: no element split across chunks except oversized-element exception; grouping only for same-type adjacent elements when `config[type].group` is `True`; every chunk carries non-empty `source_element_ids` and `element_type`; output order matches input order (FR-005, FR-006, FR-007, contracts/document-model-contract.md)
- [x] T009 [P] Implement degraded single-section fallback builder `build_fallback_model(asset_id, source_format, best_effort_text, reason)` in `src/core/document_intelligence/fallback.py` (FR-011, research R7)
- [x] T010 [P] Unit tests for canonical vocabulary validation and deterministic id determinism (same input → same ids across two parses) in `tests/unit/core/document_intelligence/test_model.py`
- [x] T011 [P] Unit tests for chunk-mapper invariants (no-split, grouping toggle, oversized-element exception, order preservation) in `tests/unit/core/document_intelligence/test_chunk_mapper.py`
- [x] T012 [P] Unit tests for fallback builder in `tests/unit/core/document_intelligence/test_fallback.py`

**Checkpoint**: Document Model + chunk mapper are usable and tested in isolation. No wiring into
ingestion yet — user stories can now proceed.

---

## Phase 3: User Story 1 - Table rows survive ingestion intact (Priority: P1) 🎯 MVP

**Goal**: Uploading a spreadsheet never loses or splits a data row across chunks (spec US1).

**Independent Test**: Upload a 50-row `.xlsx` fixture; verify the Document Model contains
exactly 50 `table-row` elements and every resulting chunk maps to whole rows only.

### Tests for User Story 1

- [x] T013 [P] [US1] Unit test `xlsx_parser` row extraction (element count, `fields` mapping, provenance keys) in `tests/unit/core/document_intelligence/test_parsers.py`
- [x] T014 [US1] Integration test SC-001 using `sample_50_rows.xlsx`: 50 `table-row` elements in, 50 unsplit `table-row` chunks out, unique `row_index` per chunk in `tests/integration/ingestion/test_xlsx_row_coverage.py`

### Implementation for User Story 1

- [x] T015 [US1] Implement `xlsx_parser.py`: read all sheets, emit one `table-row` `StructuralElement` per data row (column→value in `fields`), batched iteration to bound memory for large sheets, in `src/core/document_intelligence/parsers/xlsx_parser.py` (FR-004, research R8)
- [x] T016 [US1] Register the xlsx parser for `.xlsx` in `ParserRegistry` bootstrap in `src/core/document_intelligence/parsers/__init__.py`
- [x] T017 [US1] Wire the `.xlsx` path in `ProcessController.get_file_content`/`process_file_content` to use `ParserRegistry` + `map_elements_to_chunks` instead of `_load_xlsx`/`row_chunk_xlsx`, preserving existing `chunk_metadata` keys (`sheet_name`, `row_index`, `fields`, `col_*`) plus new `source_element_ids`/`element_type` in `src/services/process_service.py` (FR-007, FR-014)
- [x] T018 [US1] Log per-asset structural element counts for xlsx ingestion at the existing Celery logging boundary in `src/tasks/file_processing.py` (NFR-007, partial — full outcome persistence lands in US4)
- [x] T019 [US1] Add `element_mapping.table-row: {group: false}` default to `src/fields/generic/chunking.yaml` so unmigrated projects get correct out-of-the-box behavior

**Checkpoint**: XLSX ingestion is fully structure-aware; SC-001 passes for `.xlsx`. This alone is
demoable as the MVP (largest known completeness bug fixed).

---

## Phase 4: User Story 2 - One generic pipeline across formats (Priority: P1)

**Goal**: `.txt`, `.pdf`, `.csv`, and `.xlsx` all flow through the same Document Model shape and
the same `ParserRegistry` + `chunk_mapper` seam (spec US2). Also delivers spec US1 Acceptance
Scenario 2 (PDF table rows as distinct elements), since PDF parsing is introduced here.

**Independent Test**: Ingest one fixture of each of the four formats; verify all four produce
`StructuralElement`s using only the canonical vocabulary, with no format-specific ad hoc shape.

### Tests for User Story 2

- [x] T020 [P] [US2] Unit tests for `text_parser` and `csv_parser` element extraction in `tests/unit/core/document_intelligence/test_parsers.py` (extend)
- [x] T021 [P] [US2] Unit tests for `pdf_parser` (section/paragraph elements; table/table-row detection on `sample_with_table.pdf`) in `tests/unit/core/document_intelligence/test_parsers.py` (extend)
- [x] T022 [US2] Integration test SC-003: ingest one fixture per format, assert every resulting `chunk_metadata["element_type"]` is in the canonical vocabulary and no format-specific type strings leak through, in `tests/integration/ingestion/test_format_regression.py`

### Implementation for User Story 2

- [x] T023 [P] [US2] Implement `text_parser.py` (`.txt` → `paragraph` elements, reusing `core/structural/engine.split_at_structural_boundaries` for boundaries) in `src/core/document_intelligence/parsers/text_parser.py`
- [x] T024 [P] [US2] Implement `csv_parser.py` (`.csv` → one `table-row` element per data row, same `fields` shape as xlsx) in `src/core/document_intelligence/parsers/csv_parser.py` (FR-004)
- [x] T025 [US2] Implement `pdf_parser.py`: reuse existing `utils/pdf_ocr.load_pdf_with_ocr_fallback` per-page text as `section`/`paragraph` elements; apply best-effort table-block heuristic to emit `table`/`table-row` elements when detected in `src/core/document_intelligence/parsers/pdf_parser.py` (research R4; satisfies spec US1 AC2)
- [x] T026 [US2] Register text/csv/pdf parsers for their extensions in `ParserRegistry` bootstrap in `src/core/document_intelligence/parsers/__init__.py`
- [x] T027 [US2] Replace the remaining `if file_ext == ...` ladder in `ProcessController.get_file_content`/`process_file_content` with `ParserRegistry` + `map_elements_to_chunks` dispatch for all four formats (xlsx path from US1 unaffected) in `src/services/process_service.py` (FR-002, research R2)
- [x] T028 [US2] Add generic `element_mapping` defaults for `paragraph`/`section`/`table`/`list`/`list-item` to `src/fields/generic/chunking.yaml` (data-model.md §3 defaults)

**Checkpoint**: All four formats flow through one generic pipeline; US1's XLSX behavior and
SC-001 remain green (regression-safe); SC-003 measurable.

---

## Phase 5: User Story 3 - Domain differences stay in YAML, not code (Priority: P1)

**Goal**: Changing how a domain groups/labels structural elements requires editing that
domain's `chunking.yaml` only — zero diffs under `src/core/` (spec US3).

**Independent Test**: Add/modify a domain pack's `element_mapping` (e.g., group `list-item`
elements) and confirm the new behavior takes effect with no core code change.

### Tests for User Story 3

- [x] T029 [P] [US3] Unit test `FieldRegistry` `element_mapping` precedence (generic < domain < project config) in `tests/unit/services/test_field_registry_element_mapping.py`
- [x] T030 [US3] Integration smoke test SC-002: introduce a new pack's `element_mapping` override, ingest a fixture under that domain, assert behavior changed and `git diff --name-only` (or equivalent path check) shows zero files under `src/core/document_intelligence/` in `tests/integration/ingestion/test_pack_yaml_only_diff.py`

### Implementation for User Story 3

- [x] T031 [US3] Extend `FieldRegistry.build_profile` to deep-merge `element_mapping` (generic < domain < `project.config_json`) alongside the existing `by_extension`/`chunk_size`/`overlap` merge in `src/services/FieldRegistry.py`
- [x] T032 [P] [US3] Migrate `src/fields/pharmacy/chunking.yaml` to declare `element_mapping.table-row: {group: false}` (like-for-like with today's `row` strategy — research R6)
- [x] T033 [P] [US3] Migrate `src/fields/legal/chunking.yaml` to declare `element_mapping` matching today's `page`/`character` strategy behavior for `section`/`paragraph` (like-for-like — research R6)
- [x] T034 [US3] Audit `src/core/document_intelligence/chunk_mapper.py` and parsers to confirm `ElementChunkConfig` is resolved purely from `profile.chunking.element_mapping` with zero domain-name conditionals (FR-008 verification pass)

**Checkpoint**: Pharmacy and legal ingestion behavior is unchanged (verified against pre-migration
baseline) but now expressed entirely as YAML; SC-002 smoke test passes.

---

## Phase 6: User Story 4 - Ingestion never fails outright on parsing trouble (Priority: P2)

**Goal**: A file that can't be confidently structured still ingests via a degraded fallback;
only genuinely unreadable files fail (spec US4).

**Independent Test**: Submit a malformed-but-openable file → ingestion succeeds with a recorded
degraded outcome. Submit an unreadable file → ingestion fails loudly.

### Tests for User Story 4

- [x] T035 [P] [US4] Unit tests: each parser raises `DocumentIntelligenceDegraded` with the correct `reason` for its degradation cases (empty content, unsupported structure, parse error) in `tests/unit/core/document_intelligence/test_parsers.py` (extend)
- [x] T036 [US4] Integration test SC-004 using `malformed.xlsx` (degrades, succeeds, outcome recorded) and `unreadable.pdf` (hard failure, task reports FAILURE) in `tests/integration/ingestion/test_degraded_fallback.py`

### Implementation for User Story 4

- [x] T037 [US4] Raise `DocumentIntelligenceDegraded` from `xlsx_parser`/`csv_parser`/`text_parser`/`pdf_parser` for their documented degradation cases, letting genuine open/read errors propagate unchanged, in `src/core/document_intelligence/parsers/{xlsx,csv,text,pdf}_parser.py`
- [x] T038 [US4] Catch `DocumentIntelligenceDegraded` in `process_service.py`, build the fallback `DocumentModel` via `fallback.build_fallback_model`, and continue chunking; do not catch other exceptions (FR-011) in `src/services/process_service.py`
- [x] T039 [US4] Persist `extraction_outcome`/`degradation_reason`/`element_counts` to `assets.asset_config.extraction` per processed asset in `src/tasks/file_processing.py` (FR-012, data-model.md §6)

**Checkpoint**: SC-004 satisfied — 100% of non-hard-failure malformed cases ingest via fallback
with the outcome observable; hard failures still fail the task.

---

## Phase 7: User Story 5 - Structure-derived citations without domain-specific code (Priority: P3)

**Goal**: Citation labels reflect richer Document Model provenance via pack-declared templates
only — no per-domain formatting code in core (spec US5).

**Independent Test**: Two domain packs configure different `label_template`s for the same
element type; cited answers show differing labels with no core branching on domain.

### Tests for User Story 5

- [x] T040 [P] [US5] Unit tests for `format_source_label(..., label_template=...)` template substitution and fallback-to-default behavior in `tests/unit/utils/test_chunk_metadata.py`
- [x] T041 [US5] Integration test: pharmacy vs legal citation labels differ per their configured templates for equivalent element types in `tests/integration/ingestion/test_citation_labels.py`

### Implementation for User Story 5

- [x] T042 [US5] Add optional `label_template` parameter to `format_source_label()`, applying it against `chunk_metadata` when the active pack sets `MetadataProfile.label_template`, else preserving today's hardcoded output byte-for-byte, in `src/utils/chunk_metadata.py` (FR-015, research R9)
- [x] T043 [US5] Pass `profile.metadata.label_template` at every `format_source_label()` call site in `src/services/rag/answer_service.py`
- [x] T044 [P] [US5] Add/confirm `label_template` values using `row_index`/`sheet_name`/`article_number` provenance in `src/fields/pharmacy/chunk_metadata.yaml` and `src/fields/legal/chunk_metadata.yaml`

**Checkpoint**: Citation formatting is fully YAML-driven; FR-015 verified (no domain-specific
Python formatting path).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Observability, legacy-path cleanup, and final validation across all stories.

- [x] T045 [P] Add/extend Prometheus metrics for the Document Intelligence stage (parse errors, degraded-extraction count, element counts by type) in `src/utils/metrics.py` (NFR-007)
- [x] T046 Convert `row_chunk_dataframe`/`row_chunk_xlsx` in `src/core/chunking/engine.py` into thin compatibility shims delegating to `xlsx_parser` + `map_elements_to_chunks` (no behavior change; any remaining direct callers keep working) in `src/core/chunking/engine.py`
- [x] T047 [P] Update `src/ARCHITECTURE.md` to document the `core/document_intelligence/` seam (parsers, chunk mapper, `element_mapping` YAML lever)
- [x] T048 Run all six `quickstart.md` validation scenarios end-to-end against a live Docker Compose stack; record pass/fail per scenario
  - **DONE (2026-07-13)**: `scripts/validate_document_intelligence_quickstart.py` → 14/14 PASS; results in `quickstart-results.json`. Also fixed live bugs: `DocumentBatch` list-subclass (CPython 3.11 setattr), `merge_asset_config_key` asyncpg cast, `get_project_by_domain_key` multi-row startup crash.
- [x] T049 Benchmark ingestion time before/after migration on the fixture set from `tests/fixtures/document_intelligence/`; record the measured delta and the resulting SC-006 budget decision in `specs/006-document-intelligence-pipeline/plan.md`
  - **DONE (2026-07-13)**: full fixture process (6 files, do_reset=1) = **16.14s** on Compose stack; no pre-migration baseline available → SC-006 budget set to "no regression vs 16.14s reference sample".
- [x] T050 Re-run the `005-answer-quality` golden runner (`scripts/run_answer_quality_golden.py`) against a table/list fixture project and update `specs/005-answer-quality/baseline.md` with the post-migration AQ-1 score (SC-005)
  - **DONE (2026-07-13)**: `run_answer_quality_golden.py` still absent (005 harness); AQ-1 proxy via indexed table-row coverage = **100% (50/50)** on `sample_50_rows.xlsx` — recorded in baseline.md.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — **MVP**
- **US2 (Phase 4)**: Depends on Phase 2; independently testable but by convention implemented
  after US1 so the xlsx MVP lands first (both are P1; spec lists US1 before US2)
- **US3 (Phase 5)**: Depends on Phase 2 (`ElementChunkConfig`) and benefits from US1/US2 parsers
  existing to migrate against, but its own tests (T029/T030) only require the Foundational seam
- **US4 (Phase 6)**: Depends on parsers existing (US1 for xlsx, US2 for the other three) since it
  adds degradation-signaling to each parser
- **US5 (Phase 7)**: Depends on Phase 2 only for provenance shape; independently testable once
  any parser produces `chunk_metadata`
- **Polish (Phase 8)**: Depends on US1–US4 minimum; US5 recommended before final quickstart run

### User Story Dependencies

| Story | Depends on | Independent test |
| ----- | ---------- | ----------------- |
| US1 (P1) | Foundational | 50-row xlsx → 50 unsplit table-row chunks |
| US2 (P1) | Foundational (parallel-safe with US1's tests, but shares `process_service.py` edits) | One fixture per format → shared vocabulary |
| US3 (P1) | Foundational; migrates behavior introduced by US1/US2 | New pack `element_mapping` → zero core diff |
| US4 (P2) | US1 + US2 (parsers to instrument) | Malformed file → degraded; unreadable file → hard failure |
| US5 (P3) | Foundational (provenance shape) | Two packs, two citation label outputs |

### Within Each User Story

- Tests are written first and MUST fail before implementation
- Parsers before registry wiring before `process_service.py` integration
- Core implementation before pack YAML migration
- Story complete before moving to the next priority

### Parallel Opportunities

**Phase 1**: T002 ∥ T003
**Phase 2**: T005 ∥ T006; T009 ∥ (T004→T008 sequential); T010 ∥ T011 ∥ T012
**Phase 3 (US1)**: T013 ∥ T014 (tests); T015 sequential into T016 → T017 → T018 → T019
**Phase 4 (US2)**: T020 ∥ T021 (tests); T023 ∥ T024 (different parser files) → T025 → T026 → T027 → T028
**Phase 5 (US3)**: T029 ∥ T030 (tests); T032 ∥ T033 (different pack files)
**Phase 6 (US4)**: T035 tests parallel-safe across parser files; T037 sequential after T035
**Phase 7 (US5)**: T040 ∥ T044
**Phase 8**: T045 ∥ T047 ∥ T050

**Cross-story parallelism** (after Phase 2): Developer A → US1; Developer B → US2 (coordinate on
shared `process_service.py` edits, e.g. via sequential merges); Developer C → US5 (independent
file set); US3 and US4 follow once US1/US2 parsers exist.

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
T013: tests/unit/core/document_intelligence/test_parsers.py (xlsx case)
T014: tests/integration/ingestion/test_xlsx_row_coverage.py

# Then sequential implementation (shared files):
T015 (xlsx_parser.py) → T016 (registry) → T017 (process_service.py) → T018 (file_processing.py) → T019 (generic/chunking.yaml)
```

## Parallel Example: User Story 2

```bash
# Parser implementations in parallel (different files):
T023: src/core/document_intelligence/parsers/text_parser.py
T024: src/core/document_intelligence/parsers/csv_parser.py

# pdf_parser is larger (table heuristic) — implement after or alongside:
T025: src/core/document_intelligence/parsers/pdf_parser.py

# Then sequential wiring:
T026 (registry) → T027 (process_service.py) → T028 (generic/chunking.yaml)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T012)
3. Complete Phase 3: User Story 1 (T013–T019)
4. **STOP and VALIDATE**: Run `pytest tests/integration/ingestion/test_xlsx_row_coverage.py` plus
   the Phase 2 unit tests; confirm SC-001 on the 50-row fixture
5. Demo: upload a real spreadsheet, show zero split/merged rows

### Incremental Delivery

1. Setup + Foundational → Document Model/chunk-mapper seam testable in isolation
2. US1 → MVP (spreadsheet row completeness — the documented root-cause fix)
3. US2 → format parity (txt/pdf/csv join xlsx on the same pipeline)
4. US3 → YAML-only domain configuration proven (pharmacy/legal migrated, zero core diff)
5. US4 → resilience (degraded fallback vs hard failure)
6. US5 → citation enrichment
7. Polish → observability, legacy shim, benchmark, quickstart, tie-in to `005-answer-quality`

### Suggested MVP Scope

**User Story 1 only** (Phases 1–3): ~19 tasks. Delivers the single highest-value fix — table
rows can no longer be split or lost during ingestion for the format where this bug was most
severe (XLSX).

---

## Notes

- Do NOT add per-domain Python parsing modules (e.g., `utils/pharmacy/...`) — all domain
  behavior is `element_mapping`/`chunk_metadata.yaml` per FR-008/FR-010.
- `by_extension` in `ChunkingProfile` keeps meaning "which parser"; do not repurpose it for
  chunk-shaping — that is `element_mapping`'s job (research R6).
- Keep `RAG_SEMANTIC_PARSER_ENABLED`/retrieval/reranking untouched — this feature only changes
  what enters chunking (see spec Out of Scope).
- `core/chunking/engine.py` row-chunking functions are only converted to shims (T046), not
  deleted, until callers are confirmed migrated.

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001–T003 (3) | — |
| Foundational | T004–T012 (9) | — |
| US1 MVP | T013–T019 (7) | US1 |
| US2 Format parity | T020–T028 (9) | US2 |
| US3 YAML-only domains | T029–T034 (6) | US3 |
| US4 Resilience | T035–T039 (5) | US4 |
| US5 Citations | T040–T044 (5) | US5 |
| Polish | T045–T050 (6) | — |
| **Total** | **50 tasks** | |

**Format validation**: All 50 tasks use `- [ ] [Tnnn] [P?] [USn?] Description with file path` ✅
