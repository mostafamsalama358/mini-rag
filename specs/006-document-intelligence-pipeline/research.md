# Research: Document Intelligence Pipeline

**Feature**: `006-document-intelligence-pipeline` | **Date**: 2026-07-11

Each item resolves one technical unknown or technology choice from Phase 0, grounded in the
current codebase (`src/services/process_service.py`, `src/core/chunking/engine.py`,
`src/tasks/file_processing.py`, `src/fields/schemas.py`).

---

## R1 — Document Model representation

**Decision**: Pydantic models (`DocumentModel`, `StructuralElement`) in `core/document_intelligence/model.py`, mirroring the existing convention in `fields/schemas.py` and `core/query_parser/schema.py` (Pydantic for validated cross-boundary data shapes).

**Rationale**: Constitution IV requires Pydantic-backed schemas; the Document Model crosses a boundary (parsers → chunk mapper → indexing task) and benefits from validation (canonical `type` enum, required provenance keys per type) and easy `.model_dump()` for logging/debugging.

**Alternatives considered**:

| Alternative | Rejected because |
| Plain dataclasses (like current `Document`/`PdfPageDocument`) | No validation of the canonical element-type vocabulary (FR-001a); easy to typo a `type` string with no error |
| A full third-party document schema (e.g., adopting Docling's `DoclingDocument`) | Ties core to one OCR/parsing vendor; violates provider-swappability (Constitution V) since Docling is only one of two configured OCR engines today |

---

## R2 — Parser registry (Open/Closed for new formats)

**Decision**: A small `ParserRegistry` in `core/document_intelligence/parsers/__init__.py` mapping file extension → a `DocumentParser` protocol implementation (`parse(file_path, file_id) -> DocumentModel`). `process_service.py` calls `get_parser_for_extension(ext)` instead of the current `if file_ext == ProcessingEnum.X.value:` ladder.

**Rationale**: Constitution III (Open/Closed) — today `ProcessController.get_file_content` is an if/elif chain per extension (`process_service.py` L58-84); adding format support means extending the ladder. A registry lets each parser be added/tested independently and mirrors the existing `LLMProviderFactory` / `VectorDBProviderFactory` pattern already used for providers (Constitution V), applied here to parsers.

**Alternatives considered**:

| Alternative | Rejected because |
| Keep the if/elif ladder, just call a shared helper at the end | Doesn't fix the Open/Closed violation; still grows unbounded per format |
| One mega-parser with per-format branches inside | Same problem moved one level down; harder to unit-test per format |

---

## R3 — Stable Structural Element identifier (FR-003a)

**Decision**: `element.id = f"{asset_fingerprint}:{element_path}"` where `element_path` is the element's ordered position expressed as a stable path (e.g., `sheet:0/row:41`, `page:3/para:2`, `section:2/table:0/row:7`). `asset_fingerprint` reuses the existing per-asset fingerprint mechanism already computed in `tasks/file_processing.py` (`build_asset_fingerprint`) so identifiers are stable across re-processing of unchanged files and change only when the underlying file content changes.

**Rationale**: FR-003a requires determinism from "document identity and structural position." The codebase already has an asset-fingerprint primitive (`utils/project_assets.py`) used for idempotency; reusing it avoids inventing a second identity scheme and keeps `element.id` stable across retries (supports FR-013 idempotency and SC-004 observability of degraded runs).

**Alternatives considered**:

| Alternative | Rejected because |
| Random UUID per element | Not deterministic — violates FR-003a (same source must yield same ids) and breaks idempotent re-processing checks |
| Sequential integer counter only | Not stable if element order shifts slightly between parser versions; no document-identity component |

---

## R4 — Table detection inside PDFs (best-effort)

**Decision**: Reuse the existing PyMuPDF-based page extraction (`utils/pdf_ocr.py`) as the text source; add a lightweight heuristic pass (consistent multi-column whitespace / repeated delimiter patterns per line) to segment probable table blocks into `table`/`table-row` elements, falling back to `paragraph` elements when no confident table structure is detected. This is explicitly best-effort per spec Assumptions/Out-of-Scope (no perfect layout fidelity for merged/nested cells in v1).

**Rationale**: Introducing a full layout-aware PDF table parser (e.g., wiring Docling's `DocumentConverter` directly on PDFs, currently only used for single OCR page images per `utils/docling_ocr.py`) is a larger, separately-justifiable change; the spec explicitly scopes PDF table fidelity as best-effort for v1 (Out of Scope: "Perfect-fidelity layout reconstruction").

**Alternatives considered**:

| Alternative | Rejected because |
| Full Docling `DocumentConverter` on every PDF | Bigger dependency/perf footprint than justified by this feature's stated v1 scope; candidate for a future feature if table fidelity becomes a blocking need |
| No table detection in PDFs at all (page = one section) | Leaves the PDF table-row completeness gap (SC-001) unaddressed for PDF sources, only fixing XLSX/CSV |

---

## R5 — No-split guarantee algorithm (FR-005/FR-006)

**Decision**: `chunk_mapper.py` builds chunks by walking the Document Model's ordered elements and greedily grouping adjacent elements of the same type while the running character budget (from the pack's `ElementChunkConfig.max_chunk_chars`) is not exceeded; an element that alone exceeds the budget becomes its own chunk (oversized-element path, explicitly allowed by FR-005) rather than being split — the char-splitter fallback used for prose can still run inside an oversized `paragraph`/`section` element as a documented exception.

**Rationale**: This preserves today's proven pharmacy row-chunking behavior (`row_chunk_dataframe`, `core/chunking/engine.py`) generically for any `table-row` element and any domain, while adding grouping for `list-item`/short-`paragraph` elements that today are needlessly one-chunk-per-line in row mode.

**Alternatives considered**:

| Alternative | Rejected because |
| Always one chunk per element, never group | Wastes retrieval slots on many tiny chunks (e.g., very short rows), regressing the exhaustive-limit economics documented in `001`/`005` |
| Character-split first, structure-tag after | Reintroduces the exact row-splitting bug this feature exists to fix |

---

## R6 — Migration of `chunking.yaml` (`by_extension` → `element_mapping`)

**Decision**: Keep `by_extension` in `ChunkingProfile` to select **which parser** runs per format (parser selection is still format-based — a `.pdf` is always parsed by the PDF parser). Add a new `element_mapping: dict[str, ElementChunkConfig]` block (keyed by canonical element type: `table-row`, `paragraph`, `list-item`, …) that replaces the current strategy names (`character`/`page`/`row`) as the lever for **how elements become chunks**. Existing pack YAML (`generic`, `pharmacy`, `legal`) is updated to express today's behavior (e.g., pharmacy's `row` strategy → `element_mapping.table-row: {group: false}`) as a like-for-like migration, not a behavior change.

**Rationale**: Directly satisfies FR-009/FR-010 (domain packs configure element handling purely via YAML) while not discarding the extension-based parser selection, which is a format concern, not a domain concern (US2).

**Alternatives considered**:

| Alternative | Rejected because |
| Replace `by_extension` entirely with element-type-only config | Parser selection still needs to know the raw format; collapsing the two concerns would require format-sniffing logic inside the mapping, adding complexity without benefit |
| Introduce a brand-new YAML file per pack for element mapping | Unnecessary proliferation; `chunking.yaml` is already the natural home per existing pack layout |

---

## R7 — Fallback / degraded path trigger conditions (FR-011/FR-012)

**Decision**: A parser signals degradation by raising a typed `DocumentIntelligenceDegraded` exception (with a reason: `unsupported_structure` | `parse_error` | `empty_content`) which `process_service.py` catches to construct a single-section fallback `DocumentModel` (whole extracted text as one `section` element) and sets `DocumentModel.extraction_outcome = "degraded"` with the reason recorded. A **hard failure** (file cannot be opened/read at all — e.g., corrupted zip for `.xlsx`, unreadable PDF) is NOT caught here and propagates as an ingestion failure, matching today's `if file_content is None: logger.error(...); continue` behavior in `tasks/file_processing.py`.

**Rationale**: Matches FR-011's explicit split between "fell back to degraded" (must succeed) and "hard failure" (must fail loudly) and reuses the existing exception-boundary pattern already present in `_load_xlsx` (`except Exception: return None`).

**Alternatives considered**:

| Alternative | Rejected because |
| Silently degrade on any exception, including unreadable files | Violates FR-011's explicit carve-out; would hide real corruption as if it were a content-shape edge case |
| Return `None`/`False` sentinels instead of a typed exception | Current codebase already does this in places (`_load_xlsx`) and it is hard to distinguish "no content" from "parse error" downstream — a typed exception with a reason is clearer for FR-012 observability |

---

## R8 — Large table streaming/batching

**Decision**: `xlsx_parser.py`/`csv_parser.py` iterate rows in bounded batches (reusing pandas `chunksize`/`iterrows` in batches, matching the existing `row_chunk_dataframe` iteration style) rather than materializing all `StructuralElement` instances plus all `Chunk` instances in memory simultaneously for very large sheets; batch size is a core-level constant informed by existing Celery worker memory practices (Constitution X), not a per-domain YAML knob.

**Rationale**: Spec Edge Case explicitly calls out "tens of thousands of rows" must not cause unbounded memory growth; today's `row_chunk_dataframe` already loads the whole DataFrame via `pd.read_excel(..., sheet_name=None)` — this decision keeps that read but bounds element/chunk materialization downstream, deferring a full streaming-read redesign as out of scope unless profiling shows the DataFrame load itself is the bottleneck.

**Alternatives considered**:

| Alternative | Rejected because |
| Full streaming XLSX read (e.g., `openpyxl` read-only mode) | Larger change to the extraction layer than justified without a measured memory problem; candidate follow-up if SC-006 perf budget is missed |
| No batching, rely on Celery worker memory limits alone | Directly risks worker OOM on genuinely large sheets; contradicts the edge case requirement |

---

## R9 — Citation label enrichment wiring (FR-014/FR-015)

**Decision**: Close the existing gap where `MetadataProfile.label_template` is loaded but never read by `utils/chunk_metadata.format_source_label()`. `format_source_label` gains an optional `label_template: str | None` parameter; callers (`answer_service.py`) pass `profile.metadata.label_template` when set, falling back to today's hardcoded `{file_name} — page {page}` format when absent (generic pack default) — preserving current output byte-for-byte for packs that don't set a template.

**Rationale**: FR-015 requires citation formatting to be YAML-driven, not per-domain Python; this was already the intent of `chunk_metadata.yaml` (`002-field-registry`) but the wiring was left incomplete. Structural Element provenance (e.g., `section_path`, richer `row_index`/`sheet_name`) gives templates more to work with once Document Intelligence lands.

**Alternatives considered**:

| Alternative | Rejected because |
| Leave `format_source_label` hardcoded, add a second domain-specific formatter | Reintroduces per-domain formatting logic in core, violating FR-015 |
| Defer citation wiring entirely to a later feature | Leaves a known, already-documented gap (`002-field-registry` research R9) unresolved despite this feature producing richer provenance that motivates fixing it now |

---

## R10 — Testing & fixture strategy (ties to `005-answer-quality`)

**Decision**: Golden fixtures for this feature live under `tests/fixtures/document_intelligence/` (small synthetic `.xlsx`/`.csv`/`.pdf`/`.txt` files with a known row/paragraph count) and are asserted against directly (element counts, chunk counts, no-split invariant) in unit/integration tests — separate from, but compatible with, the `tests/golden/answer_quality/` harness from `005-answer-quality`, which consumes the resulting improved retrieval coverage (AQ-1) as an end-to-end signal rather than re-testing Document Intelligence internals.

**Rationale**: Keeps this feature's tests fast and unit-level (no LLM calls needed to verify "50 rows in → 50 table-row elements out"), while `005-answer-quality`'s golden set remains the place where the *end-to-end* completeness improvement is measured.

**Alternatives considered**:

| Alternative | Rejected because |
| Only test via the `005-answer-quality` golden set | Couples a structural/deterministic guarantee (no split rows) to a slower, LLM-dependent harness; regressions would be hard to localize |
