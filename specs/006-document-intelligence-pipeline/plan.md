# Implementation Plan: Document Intelligence Pipeline

**Branch**: `006-document-intelligence-pipeline` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-document-intelligence-pipeline/spec.md`

## Summary

Insert a generic **Document Intelligence** stage between raw file extraction and chunking:
every supported format (`.txt`, `.pdf`, `.csv`, `.xlsx`) is parsed into a structured
**Document Model** (ordered `StructuralElement`s using a canonical, extensible vocabulary —
`section`, `paragraph`, `table`, `table-row`, `list`, `list-item`, each with a stable
deterministic id and provenance). Chunking is then derived from these elements — never
splitting one element across chunks except a documented oversized-element exception — instead
of today's ad hoc per-format text/CSV-blob handling. Domain differences (which element types
get grouped, which extra metadata surfaces) are configured entirely via a new
`element_mapping` block in each pack's `chunking.yaml`; the core module contains zero
domain-name conditionals. A degraded single-section fallback keeps ingestion resilient when
structure can't be confidently recovered, while genuinely unreadable files still fail loudly.
This closes the root cause of incomplete list/table answers (`001-pharmacy-query-enhancement`
R1/R4) and is the prerequisite structural fix that `005-answer-quality`'s AQ-1/AQ-2 retrieval
coverage targets depend on.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic, Celery; existing
extraction stack reused as-is: PyMuPDF (`fitz`) for PDF text, `pandas` for XLSX/CSV, LangChain
`TextLoader`/`CSVLoader`/`RecursiveCharacterTextSplitter`, existing OCR providers (Gemini
Vertex, Docling/RapidOCR) behind `OCR_ENGINE`.

**Storage**: PostgreSQL + pgvector (unchanged). `chunks.chunk_metadata` JSONB gains
`source_element_ids` + `element_type` keys; `assets.asset_config` JSONB gains an `extraction`
key (outcome/reason/element_counts) alongside the existing `field_manifest` key.

**Testing**: pytest + pytest-asyncio; new `tests/unit/core/document_intelligence/` (parser →
model, chunk mapper invariants, fallback path) and `tests/integration/ingestion/` (format
regression, row-coverage fixture, YAML-only-diff smoke test) per `research.md` R10.

**Target Platform**: Linux containers via Docker Compose (existing deployment target;
unchanged by this feature).

**Project Type**: Single backend web service (FastAPI + Celery workers) — no frontend changes.

**Performance Goals**: No regression in ingestion throughput/success rate for the four
existing formats (SC-003); large tables (tens of thousands of rows) processed without
unbounded memory growth via bounded batching (research R8); exact SC-006 time-regression
budget to be measured against baseline during implementation and recorded in
`specs/006-document-intelligence-pipeline/` once available (no fixed number available before
a first benchmark run — tracked as an implementation-phase measurement, not a spec blocker).

**SC-006 status (2026-07-13)**: Live Compose timing on
`tests/fixtures/document_intelligence/` (6 files, `do_reset=1`, project_id=1):
**16.14s** end-to-end process task. No pre-migration baseline existed in-repo;
budget = keep future runs within ~2× this reference (≤ ~32s on the same host/
Compose profile) unless hardware changes. Full pass/fail log:
`specs/006-document-intelligence-pipeline/quickstart-results.json`.

**Constraints**: Zero domain-name conditionals in `src/core/document_intelligence/` (FR-008);
no core code changes required to alter a domain's element handling (FR-010); idempotent
re-processing (FR-013); hard file-read failures MUST propagate as failures, never silently
degrade (FR-011).

**Scale/Scope**: 4 raw formats, 6 canonical structural element types (v1), 3 existing field
packs (`generic`, `pharmacy`, `legal`) migrated to the new `element_mapping` config
like-for-like (research R6) as part of this feature's rollout.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ☑ — Document Model + chunk-mapping logic in `core/document_intelligence/` (application/core); OCR/loader I/O stays in `utils/`/`services/process_service.py` (infrastructure); Celery orchestration in `tasks/` unchanged |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ☑ — new `core/document_intelligence/` slice with its own `tests/unit/.../document_intelligence/` and `tests/integration/ingestion/` |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ☑ — `ParserRegistry` (research R2) replaces the if/elif extension ladder in `process_service.py`; each format parser implements the `DocumentParser` protocol (`contracts/document-model-contract.md`) |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic schemas | ☑ — `DocumentModel`/`StructuralElement`/`ElementChunkConfig` are Pydantic (research R1); parsing remains Celery-worker-bound CPU work (not an HTTP hot path), consistent with existing OCR threading |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ☑ — no changes to retrieval/reranking/prompting; citations preserved and enriched via completed `label_template` wiring (FR-014/FR-015, research R9) |
| G6 Testing | Unit and integration tests planned for changed behavior | ☑ — planned per Technical Context/Testing above and `research.md` R10 |
| G7 Observability | Structured logging + metrics at new async boundaries | ☑ — `extraction_outcome`, `degradation_reason`, per-type element counts logged at the existing Celery task logging boundary (NFR-007); new metrics candidates identified for `/speckit-tasks` |
| G8 Security | No secrets in code; input validation; parameterized SQL | ☑ — no new secrets/providers requiring credentials; existing upload validation (`FILE_ALLOWED_TYPES`/`FILE_MAX_SIZE`) unchanged |
| G9 Performance | Long work in Celery; batching/pooling considered | ☑ — unchanged Celery placement; bounded batching for large tables (research R8) |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ☑ — no stack changes |

*All gates pass with the design in this plan; no Complexity Tracking entries required.*

## Project Structure

### Documentation (this feature)

```text
specs/006-document-intelligence-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   ├── document-model-contract.md
│   └── element-mapping-yaml-contract.md
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── document_intelligence/         # NEW — generic Document Model + parsers + chunk mapper
│   │   ├── __init__.py
│   │   ├── model.py                   # DocumentModel, StructuralElement, canonical vocabulary
│   │   ├── errors.py                  # DocumentIntelligenceDegraded (+ reason enum)
│   │   ├── parsers/
│   │   │   ├── __init__.py            # ParserRegistry, get_parser_for_extension
│   │   │   ├── text_parser.py         # .txt → paragraph elements
│   │   │   ├── csv_parser.py          # .csv → table-row elements
│   │   │   ├── xlsx_parser.py         # .xlsx → table-row elements (all sheets, batched)
│   │   │   └── pdf_parser.py          # .pdf → section/paragraph/table(-row) elements
│   │   ├── chunk_mapper.py            # StructuralElement(s) → Chunk, per ElementChunkConfig
│   │   └── fallback.py                # degraded single-section DocumentModel construction
│   ├── chunking/engine.py             # MODIFIED — row_chunk_* becomes a thin compat shim over
│   │                                     the new xlsx_parser + chunk_mapper (no behavior change)
│   ├── structural/engine.py           # UNCHANGED — reused by pdf_parser/text_parser for
│   │                                     section/paragraph boundary detection
│   └── field_resolution.py            # UNCHANGED contract — still reads table-row `fields`
├── services/
│   └── process_service.py             # MODIFIED — delegates to ParserRegistry + chunk_mapper
│                                         instead of ad hoc per-extension loaders/splitters
├── fields/
│   ├── schemas.py                     # MODIFIED — ChunkingProfile gains `element_mapping`
│   │                                     (dict[str, ElementChunkConfig])
│   └── {generic,pharmacy,legal}/chunking.yaml   # MODIFIED — add element_mapping (like-for-like
│                                                   migration, research R6)
├── tasks/file_processing.py           # MODIFIED — persists asset_config.extraction outcome;
│                                         logs element counts (NFR-007)
└── utils/
    ├── pdf_ocr.py, gemini_ocr.py, docling_ocr.py   # UNCHANGED — consumed by pdf_parser
    └── chunk_metadata.py               # MODIFIED — format_source_label reads
                                            MetadataProfile.label_template (FR-015, research R9)

tests/
├── unit/core/document_intelligence/
│   ├── test_model.py                  # FR-001a vocabulary + FR-003a stable-id determinism
│   ├── test_parsers.py                # per-format parser → structural elements
│   ├── test_chunk_mapper.py           # FR-005 no-split guarantee, FR-006 grouping
│   └── test_fallback.py               # FR-011/FR-012 degraded vs hard-failure paths
├── integration/ingestion/
│   ├── test_xlsx_row_coverage.py      # SC-001 fixture (50-row spreadsheet)
│   ├── test_format_regression.py      # SC-003 (4 formats, no regression vs baseline)
│   └── test_pack_yaml_only_diff.py    # SC-002 (new domain behavior, zero core diff)
└── fixtures/document_intelligence/    # sample_50_rows.xlsx, sample.csv, sample_with_table.pdf,
                                          sample.txt, malformed fixtures (research R10)
```

**Structure Decision**: Single-project backend (Option 1 — no frontend/mobile split needed).
The new `core/document_intelligence/` package is the generic seam mandated by the spec: format
parsers are plugins registered in `ParserRegistry` (Open/Closed, G3), and the only per-domain
lever is the `element_mapping` YAML block consumed by the generic `chunk_mapper` — no domain
name ever appears under `src/core/`. `by_extension` in `ChunkingProfile` is narrowed to mean
"which parser" (a format concern); `element_mapping` is the new "how to chunk" lever (a domain
concern), per `research.md` R6 and `contracts/element-mapping-yaml-contract.md`.

## Complexity Tracking

*No entries — all Constitution Check gates pass without justified deviation.*
