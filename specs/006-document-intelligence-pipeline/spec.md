# Feature Specification: Document Intelligence Pipeline

**Feature Branch**: `006-document-intelligence-pipeline`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "Transform raw documents into structured document models before chunking. Replace file-processing pipeline with document-intelligence pipeline. Keep generic architecture. No pharmacy logic."

## Executive Summary

The ingestion pipeline SHALL gain a new **Document Intelligence** stage that parses every raw uploaded file into a **structured Document Model** (sections, paragraphs, tables with rows/cells, list items — with provenance) **before** chunking happens. Chunking then derives chunks from structural elements of this model instead of operating on flattened raw text (whole PDF pages, concatenated XLSX-as-CSV blobs, or plain character windows).

This directly targets the root cause identified in prior work (`001-pharmacy-query-enhancement` R1/R4, `002-field-registry`): loss of row/paragraph/table boundaries during extraction causes incomplete retrieval regardless of how good the retriever or generator is. It also feeds the completeness goals of `005-answer-quality` (AQ-1/AQ-2): a retriever can only be as complete as the units it was given.

**Architectural constraint (non-negotiable for this feature)**: the Document Intelligence stage lives in **generic core** (`src/core/`). Any per-domain behavior (which structural element types matter, how they map to chunks, extra metadata keys) MUST be expressed as **YAML field-pack configuration** (`fields/{domain}/*.yaml`), never as domain-named branches in core Python. No pharmacy (or any single-domain) logic is added to the core module.

### Architectural Verdict

| Approach | Verdict |
| -------- | ------- |
| **Structured Document Model → structure-aware chunking (core) + YAML element mapping (packs)** | Preferred — single generic pipeline; domain differences stay declarative. |
| **Current pipeline**: format-specific ad hoc extraction → raw text/CSV blob → character/page/row split | Superseded for structure-bearing formats — proven to fragment rows/lists/tables (001 R1, R4). |
| **Per-domain parsing modules** (e.g., `utils/pharmacy/parse_xlsx.py`) | Rejected — violates generic-core-plus-YAML-packs principle; reintroduces per-domain Python maintenance. |
| **Full third-party document-AI service for every format** | Rejected for v1 — introduces a hard external dependency and cost for formats (txt/csv) that need none; reserved as a pluggable provider behind an interface if ever needed, per Constitution V. |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Table rows survive ingestion intact (Priority: P1)

A user uploads a spreadsheet or a PDF containing a table. Today, rows can be split across chunks or buried inside a single oversized blob chunk, so questions asking "list all X" come back incomplete. With Document Intelligence, each table row becomes one addressable structural element that chunking never splits.

**Why this priority**: This is the single largest known cause of incomplete answers in production (documented root cause in `001-pharmacy-query-enhancement`), and it blocks the completeness goals of `005-answer-quality`.

**Independent Test**: Upload a spreadsheet with 50 known rows. After ingestion, verify the Document Model contains exactly 50 table-row elements and that no chunk contains a partial row or merges two rows together.

**Acceptance Scenarios**:

1. **Given** an uploaded `.xlsx` file with N data rows, **When** ingestion completes, **Then** the Document Model exposes N table-row structural elements, each carrying its sheet name and row index, and each row maps to exactly one chunk (or a bounded group of whole rows, never a fraction of a row).
2. **Given** an uploaded `.pdf` containing an embedded table, **When** ingestion completes, **Then** table rows detected in the document are represented as distinct structural elements rather than being merged into the surrounding page paragraph text.

---

### User Story 2 - One generic pipeline across formats (Priority: P1)

A platform operator ingests documents of different raw formats (text, PDF, CSV, spreadsheet). Today each format has a different, partly inconsistent extraction path. With Document Intelligence, every supported format is parsed into the same structural model shape, so downstream chunking, metadata, and citation logic is written once.

**Why this priority**: Without a unifying model, every new format or domain need re-introduces format-specific chunking logic, working against the generic-core-plus-YAML-packs architecture.

**Independent Test**: Ingest one document of each currently supported format (`.txt`, `.pdf`, `.csv`, `.xlsx`). Verify all four produce a Document Model built from the same structural-element vocabulary (section/paragraph/table/table-row/list/list-item), even though element mixes differ per format.

**Acceptance Scenarios**:

1. **Given** any supported raw format, **When** it is parsed, **Then** the output is a Document Model instance using the shared structural-element vocabulary, not a format-specific ad hoc shape.
2. **Given** the same logical content re-uploaded in a different supported format, **When** both are ingested, **Then** the resulting structural elements are semantically comparable (e.g., a CSV row and the equivalent XLSX row both become table-row elements with equivalent metadata keys).

---

### User Story 3 - Domain differences stay in YAML, not code (Priority: P1)

A team adds a new domain (or adjusts an existing one, e.g. legal or pharmacy) and needs table rows, sections, or list items handled slightly differently — different chunk grouping, different metadata keys surfaced for citations. This SHALL be achievable by editing that domain's YAML pack only.

**Why this priority**: This is the explicit constraint driving the feature ("keep generic architecture… no pharmacy logic") and the platform's core reusability goal.

**Independent Test**: Starting from the generic pack's default element-to-chunk mapping, create/modify a domain pack YAML that changes how `table-row` elements are grouped into chunks and which metadata keys are surfaced, without touching any file under `src/core/`. Verify the new behavior takes effect for projects using that domain.

**Acceptance Scenarios**:

1. **Given** a domain pack YAML declares a mapping from structural element type to chunk grouping/metadata behavior, **When** a project using that domain is ingested, **Then** the Document Intelligence and chunking stages honor the pack's mapping without any core code change.
2. **Given** a project using the generic pack (no domain-specific YAML overrides), **When** a document is ingested, **Then** default generic behavior applies and no domain name appears anywhere in the core module's logic.

---

### User Story 4 - Ingestion never fails outright on parsing trouble (Priority: P2)

A user uploads a file that the structured parser cannot fully interpret (corrupted, unusual layout, or a format edge case). The system must still produce usable, retrievable content rather than failing the whole ingestion job.

**Why this priority**: Safety net — production ingestion must be resilient; a stricter pipeline must not regress reliability versus today's simpler one.

**Independent Test**: Submit a malformed or edge-case file for a supported extension. Verify ingestion completes (possibly with degraded structure) and the resulting asset is marked as having used a degraded/fallback extraction path.

**Acceptance Scenarios**:

1. **Given** structured parsing fails or cannot confidently identify structure for a file, **When** ingestion runs, **Then** the system falls back to a minimal degraded Document Model (e.g., whole-document text as a single section) and still produces retrievable chunks.
2. **Given** a fallback occurred, **When** the asset is later inspected (logs/metadata), **Then** the degraded-extraction outcome is recorded and observable.

---

### User Story 5 - Structure-derived citations without domain-specific code (Priority: P3)

A user reads an answer and wants to know exactly where each fact came from — which section, table, or row. Citations SHALL be derivable from the Document Model's provenance metadata using only the generic core plus each pack's declarative label/metadata configuration.

**Why this priority**: Improves trust and traceability (Constitution VI.4) but is not required for the core completeness fix and can follow after US1–US4.

**Independent Test**: Ask a question answered from a specific table row or section; verify the citation shown references that row/section's provenance (e.g., sheet + row index, or page + heading path) using the domain pack's configured label template, with no pharmacy/legal-specific code path in core.

**Acceptance Scenarios**:

1. **Given** a chunk derived from a table-row element, **When** it is cited in an answer, **Then** the citation label is built from the pack's configured template applied to that element's provenance metadata.
2. **Given** two different domain packs configure different label templates for the same element type, **When** each domain's documents are cited, **Then** the citation text differs accordingly without any core code branching on domain.

---

### Edge Cases

- Empty file or a file with no extractable content → Document Model with zero structural elements; ingestion completes with a clear "no content" outcome, no crash.
- Scanned/image-only PDF with no OCR-recoverable structure → falls back to plain-text-per-page elements (current OCR text still usable) rather than failing.
- Extremely large table (tens of thousands of rows) → Document Intelligence and chunking MUST process it within existing async/Celery worker constraints without unbounded memory growth (batched/streamed processing).
- Table with merged/nested cells or multi-row headers → system SHOULD produce a best-effort row representation rather than losing the table entirely; documented as a known-limitation edge case if perfect fidelity isn't feasible in v1.
- Document mixing languages (Arabic/English) within one table or section → structural parsing MUST NOT depend on language-specific logic; language handling remains a downstream concern (as today).
- Corrupted or truncated file that fails to open at all → ingestion fails clearly and is reported as a hard failure (not silently degraded), distinct from "parsed but low-structure" cases.
- Re-processing the same asset (retry, re-index) → MUST NOT create duplicate Document Model artifacts or duplicate chunks (idempotency preserved).
- A raw format with no current loader (e.g., `.docx`, referenced today only in legal YAML with no implementation) → explicitly out of scope for this feature unless separately added; MUST NOT be silently advertised as supported.

## Requirements *(mandatory)*

### Functional Requirements

#### Document Model & Parsing

- **FR-001**: System MUST parse each supported raw document format into a structured **Document Model** composed of ordered **Structural Elements** (e.g., section, paragraph, table, table-row, list, list-item) before any chunking occurs.
- **FR-001a**: Core MUST define a canonical structural element vocabulary consisting of `section`, `paragraph`, `table`, `table-row`, `list`, `list-item`. Additional element types MAY be added through backward-compatible extension (new type names) without changing the meaning or handling of existing types.
- **FR-002**: System MUST support, through the new Document Intelligence stage, at minimum the raw formats already supported today (`.txt`, `.pdf`, `.csv`, `.xlsx`) with no regression in ingestion success rate for these formats.
- **FR-003**: Document Model Structural Elements MUST carry provenance metadata sufficient to reconstruct source location (e.g., page number, sheet/table name, row/column index, section/heading path) as applicable to their type.
- **FR-003a**: Every Structural Element MUST have a deterministic, stable identifier derived from document identity and structural position (e.g., document id + ordered path/index within the model), such that re-parsing the same unchanged source document yields the same identifiers.
- **FR-004**: For tabular sources, each data row MUST be represented as one addressable Structural Element (table-row), preserving column-to-value mapping.

#### Chunking Derived From Structure

- **FR-005**: Chunking MUST derive chunk boundaries from Structural Elements rather than raw character offsets; a single Structural Element MUST NOT be split across multiple chunks except when it exceeds a configured maximum chunk size, in which case the split behavior MUST be explicit and documented.
- **FR-006**: System MUST allow grouping multiple adjacent Structural Elements of compatible type into one chunk (e.g., grouping short rows) when configured to do so, without breaking any single element apart.
- **FR-007**: Resulting chunks MUST inherit provenance metadata from the Structural Element(s) they were derived from.

#### Generic Core / YAML Pack Boundary

- **FR-008**: The Document Intelligence core module MUST NOT contain any domain-name-specific logic (e.g., no `if domain == "pharmacy"` or pharmacy-only parsing branches); all domain-specific behavior MUST be expressed as declarative YAML configuration consumed by generic code.
- **FR-009**: Domain field packs MUST be able to configure, via YAML only: (a) how each Structural Element type maps to chunk grouping behavior, and (b) which provenance/metadata keys are surfaced for that element type — layered over generic defaults using the existing pack precedence (generic < domain < project config).
- **FR-010**: Adding or adjusting a domain's structural-element handling MUST NOT require changes to any file under the core Document Intelligence or chunking module.

#### Resilience & Fallback

- **FR-011**: When structured parsing fails, is unsupported for a given file's actual content, or produces zero usable structure, system MUST fall back to a degraded Document Model (e.g., single whole-document text section) and MUST still complete ingestion and produce retrievable chunks — except for hard failures (file cannot be opened/read at all), which MUST be reported as ingestion failures rather than silently degraded successes.
- **FR-012**: System MUST record, per processed asset, whether Document Intelligence extraction succeeded at full structural fidelity or used a degraded/fallback path, for observability and debugging.
- **FR-013**: Ingestion and Document Model generation MUST remain idempotent — reprocessing the same asset MUST NOT duplicate chunks or Document Model artifacts.

#### Metadata & Citations

- **FR-014**: The existing chunk metadata/citation contract (source labels shown to users) MUST continue to work after migration; where the Document Model provides richer provenance, citation labels MAY be enriched but MUST NOT regress in clarity or availability.
- **FR-015**: Per-domain citation label templates and extra metadata keys MUST remain declarative (YAML), consumed by generic label-formatting code — no per-domain formatting logic in core.

### Key Entities

- **Document Model**: The structured, ordered representation of one parsed source document — a root container holding an ordered sequence of Structural Elements plus document-level metadata (source file, format, extraction outcome: full/degraded).
- **Structural Element**: One unit within a Document Model. Has a stable `id` (deterministic from document identity + structural position, per FR-003a), a `type` from the canonical vocabulary (section, paragraph, table, table-row, list, list-item — extensible per FR-001a), type-appropriate content (text, or column→value mapping for rows), and provenance metadata (page/sheet/row/section-path as applicable).
- **Chunk**: A retrieval-ready unit derived from one or more Structural Elements of compatible type, carrying inherited provenance metadata; the unit ultimately embedded and indexed.
- **Domain Pack Element Configuration**: YAML-declared, per-domain mapping from Structural Element type to (a) chunk-grouping behavior and (b) surfaced metadata keys/citation label inputs; layered over generic defaults per existing pack precedence rules.
- **Extraction Outcome**: Per-asset record of whether Document Intelligence achieved full structural extraction or fell back to a degraded path, and why (unsupported structure, parse error, empty content).

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: The Document Intelligence stage MUST respect Clean Architecture layering: format parsing/OCR integration in infrastructure (`utils/`, `stores/`), the Document Model and structure-to-chunk logic in core/application, orchestration in existing Celery tasks — no domain-specific Python outside declarative packs.
- **NFR-002**: Parsing and chunking of Document Models MUST be async/Celery-compatible for I/O- and CPU-heavy formats (PDF OCR, large spreadsheets), consistent with existing task-based ingestion.
- **NFR-003**: Any new parsing provider/library integration (e.g., a full-document layout parser) MUST be swappable via an interface/factory, consistent with existing provider architecture (Constitution V) — not hard-wired into core.
- **NFR-004**: RAG answer paths MUST continue to return source citations for every answer that uses retrieval, per existing constitution requirement, now sourced from Document Model provenance.
- **NFR-005**: Any prompt or label template changes required for richer citations MUST remain versioned/configuration-driven (YAML), not hard-coded in routes or core.
- **NFR-006**: Unit and integration tests MUST cover: Document Model construction per supported format, structure-preserving chunking (no split rows), YAML-driven per-pack behavior differences, and the degraded-fallback path.
- **NFR-007**: Structured logging MUST record, at minimum, per-asset extraction outcome (full/degraded), structural element counts by type, and resulting chunk counts, at existing Celery task logging boundaries.
- **NFR-008**: No secrets or credentials are introduced by this feature; if a new parsing provider requires credentials, they MUST follow existing secret-management rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For tabular source documents in a fixture test set, 100% of source data rows are represented as complete, unsplit retrievable chunks after ingestion (zero rows split across two chunks, zero rows merged into another row).
- **SC-002**: Adding or adjusting a domain's structural-element-to-chunk behavior requires editing that domain's YAML pack only — verified by a documented smoke test showing zero diffs under the core Document Intelligence/chunking module.
- **SC-003**: Ingestion success rate for the four currently supported formats (`.txt`, `.pdf`, `.csv`, `.xlsx`) on a regression fixture set is at or above the pre-migration baseline (no regression).
- **SC-004**: On a fixture set including intentionally malformed/edge-case files, 100% of non-hard-failure cases complete ingestion via the degraded-fallback path with the outcome recorded and observable.
- **SC-005**: On a fixture set of at least 10 documents containing tables/lists, exhaustive "list all X" style questions retrieve chunks covering the complete set of source rows/items for that entity/topic (measured against the fixture's known row count), directly improving the `005-answer-quality` AQ-1 (retrieval coverage) metric versus the pre-migration baseline.
- **SC-006**: End-to-end ingestion time for a representative fixture set does not regress by more than an agreed threshold versus the current pipeline (exact budget to be set during planning), keeping ingestion practical at current operating scale.

## Assumptions

- The four currently supported raw formats (`.txt`, `.pdf`, `.csv`, `.xlsx`) are the in-scope formats for v1; formats referenced only in YAML today without a working loader (e.g., `.docx`) remain out of scope for this feature and MUST NOT be represented as supported until implemented separately.
- Existing OCR providers (Gemini / Docling per `OCR_ENGINE` configuration) continue to supply page-level text for image-based PDF content; Document Intelligence consumes their output rather than replacing OCR itself in v1.
- The legacy raw-extraction-then-chunk code path may be retained temporarily as the implementation of the "degraded fallback" behavior (FR-011) rather than being deleted outright; full removal is an implementation-phase decision once the new pipeline is validated.
- "Generic architecture, no pharmacy logic" means: the core Document Intelligence and chunking modules contain zero domain-name conditionals; existing pharmacy-specific behavior (e.g., row chunking for pharmacy XLSX) is re-expressed as pharmacy's own YAML configuration of the generic element-mapping mechanism, not deleted as a capability.
- Table/row detection inside PDFs is best-effort; perfect layout fidelity (merged cells, multi-row headers) is not required for v1 — documented as a known limitation where not achievable.
- This feature does not change the retrieval, reranking, or generation stages themselves (those are `005-answer-quality` concerns); it changes what enters chunking, which retrieval then consumes unchanged.

## Out of Scope

- Adding new raw format support (e.g., `.docx` loader) — tracked separately if prioritized.
- Replacing or changing OCR providers/engines.
- Changes to retrieval fusion, reranking, or answer generation logic (see `005-answer-quality`).
- Any domain-specific (pharmacy, legal, etc.) parsing code added to core — all such behavior must be YAML-declared per this spec's constraints.
- Perfect-fidelity layout reconstruction for complex PDF tables (merged/nested cells) — best-effort only in v1.

## Dependencies

- `002-field-registry` — field pack precedence (generic < domain < project config) that Document Pack Element Configuration builds on.
- `003-architecture-refactor` — `core/` and `services/` layering that hosts the new Document Intelligence module.
- `005-answer-quality` — consumes the completeness improvement from structure-preserving chunking (AQ-1/AQ-2); this feature is a prerequisite for that spec's retrieval-coverage targets to be fully achievable.
- Existing OCR providers (Gemini / Docling) and file loaders (`utils/`, `services/process_service.py`) as current infrastructure this feature restructures around, not replaces.
