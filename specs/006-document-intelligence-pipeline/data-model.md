# Data Model: Document Intelligence Pipeline

**Feature**: `006-document-intelligence-pipeline` | **Date**: 2026-07-11

This document defines the entities introduced or changed by this feature. Entities map to
Pydantic models in `core/document_intelligence/model.py` (new) and extend existing models in
`fields/schemas.py`, `models/db_schemes/algorag/schemes/`.

---

## 1. StructuralElement

One unit within a parsed document. Produced by a format parser; consumed by the chunk mapper.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `id` | `str` | yes | Deterministic, stable (FR-003a). Derived `{asset_fingerprint}:{element_path}` (see research R3). |
| `type` | enum: `section`, `paragraph`, `table`, `table-row`, `list`, `list-item` | yes | Canonical vocabulary (FR-001a). Extensible — new values MAY be added without changing existing ones' meaning. |
| `order` | `int` | yes | 0-based position within the Document Model's flat ordered sequence — defines chunk-adjacency for grouping. |
| `text` | `str \| None` | one of `text`/`fields` required | Rendered text content for non-tabular types (`section`, `paragraph`, `list`, `list-item`). |
| `fields` | `dict[str, str] \| None` | one of `text`/`fields` required | Column→value mapping for `table-row` (mirrors today's `row_chunk_dataframe` `fields` view — FR-004). |
| `provenance` | `dict[str, Any]` | yes | Type-appropriate location metadata (see §4). |
| `parent_id` | `str \| None` | no | Optional link to an enclosing `section`/`table` element's `id`, for section/heading-path reconstruction (FR-012 "SHOULD preserve hierarchy"). |

**Validation rules**:
- `type` MUST be one of the canonical vocabulary values (FR-001a); unknown values are rejected at construction (Pydantic enum/`Literal`).
- Exactly one of `text` or `fields` MUST be set, matching `type` (`table-row` → `fields`; all others → `text`).
- `id` MUST be unique within a `DocumentModel` instance.

---

## 2. DocumentModel

Root container for one parsed source document.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `asset_id` | `int \| str` | yes | Matches the existing `assets.asset_id` / `file_id` this model was parsed from. |
| `source_format` | `str` | yes | File extension without dot (`txt`, `pdf`, `csv`, `xlsx`) — matches existing `source_type` chunk metadata key. |
| `elements` | `list[StructuralElement]` | yes | Ordered; may be empty (empty-file edge case). |
| `extraction_outcome` | enum: `full`, `degraded` | yes | FR-012. `full` = structured parsing succeeded; `degraded` = fallback path used. |
| `degradation_reason` | `str \| None` | required if `degraded` | One of `unsupported_structure`, `parse_error`, `empty_content` (research R7). |

**Validation rules**:
- `degradation_reason` MUST be set when `extraction_outcome == "degraded"`, and MUST be `None` otherwise.
- `elements` ordering is the canonical adjacency used by chunk grouping (FR-005/FR-006) — parsers MUST emit elements in document reading order.

**State transitions**: none (immutable value object produced once per parse call; re-processing produces a new instance with the same `asset_id`, not a mutation).

---

## 3. ElementChunkConfig (pack YAML → typed profile)

Extends `fields/schemas.py`. Declares, per canonical element `type`, how the chunk mapper should
behave — the YAML-only lever for domain differences (FR-009).

| Field | Type | Default | Notes |
| ----- | ---- | ------- | ----- |
| `group` | `bool` | `true` for `paragraph`/`list-item`; `false` for `table-row` | Whether adjacent same-type elements may be combined into one chunk. |
| `max_chunk_chars` | `int` | inherited from `ChunkingProfile.chunk_size` | Per-element-type override of the grouping character budget. |
| `metadata_keys` | `list[str]` | `[]` | Extra provenance keys from this element type to surface into `chunk_metadata` (layered over generic defaults, FR-009b). |

**`ChunkingProfile` (extended)**:

| Field | Type | Notes |
| ----- | ---- | ----- |
| `by_extension` | `dict[str, str]` | **Unchanged** — still selects which *parser* runs per raw format (research R6; format selection ≠ domain behavior). |
| `element_mapping` | `dict[str, ElementChunkConfig]` | **New** — keyed by canonical element type; layered generic < domain < project per existing precedence (`services/FieldRegistry.py` merge order). |

**Migration note**: the current `by_extension` strategy names `character`/`page`/`row` are superseded as the *chunk-shaping* lever by `element_mapping`; `by_extension` is narrowed to mean "which parser" only. Pack YAML updates are a like-for-like behavior migration (research R6), not a new capability at authoring time — though the vocabulary is now shared across every format instead of per-extension.

---

## 4. Provenance metadata shapes (by element type)

| Element type | Provenance keys | Source |
| ------------- | ---------------- | ------ |
| `section` | `page` (pdf) or `section_path` (heading hierarchy, if detected) | PDF/heading-aware parsers |
| `paragraph` | `page` (pdf) or none (txt) | all text-bearing parsers |
| `table` | `sheet_name` (xlsx) or `page` (pdf) | tabular/pdf parsers |
| `table-row` | `sheet_name`, `row_index` (xlsx/csv); `page`, `row_index` (pdf table) | mirrors today's `row_chunk_dataframe` metadata |
| `list` / `list-item` | `page` or `section_path` | text/pdf parsers, when list structure is detected |

These keys are the FR-003 "provenance metadata sufficient to reconstruct source location" and flow
unchanged into `chunk_metadata` (see §5) — no new metadata *concept* is introduced beyond what
`fields/*/chunk_metadata.yaml` already declares as `extra_keys`; this feature makes the population
of those keys structural instead of ad hoc.

---

## 5. Chunk (existing entity — fields added)

`models/db_schemes/algorag/schemes/datachunk.py` `DataChunk` is unchanged at the DB-schema level
(`chunk_text`, `chunk_metadata` JSONB, `chunk_order`). `chunk_metadata` gains two new keys, written
by the chunk mapper:

| New key | Type | Notes |
| ------- | ---- | ----- |
| `source_element_ids` | `list[str]` | The `StructuralElement.id`(s) this chunk was derived from (one for ungrouped elements, several when grouped per `ElementChunkConfig.group`). Enables FR-007 provenance inheritance and future debugging/traceability. |
| `element_type` | `str` | The canonical element type this chunk represents (e.g., `table-row`) — replaces inferring type from ad hoc keys like `row_index is not None`. |

Existing keys (`file_name`, `asset_id`, `chunk_order`, `char_count`, `page`, `sheet_name`,
`row_index`, `fields`, `col_*`) are preserved for backward compatibility (FR-014) — they are now
populated from `StructuralElement.provenance`/`fields` instead of loader-specific code paths.

---

## 6. ExtractionOutcome (per-asset record)

Persisted alongside the existing `assets.asset_config` JSONB (`field_manifest` already lives here
per `002-field-registry`), not a new table:

| Key (`asset_config.extraction`) | Type | Notes |
| -------------------------------- | ---- | ----- |
| `outcome` | `full \| degraded` | Mirrors `DocumentModel.extraction_outcome` (FR-012). |
| `reason` | `str \| None` | Set when `degraded`. |
| `element_counts` | `dict[str, int]` | Count of structural elements by type — feeds NFR-007 structured logging and SC-001 verification. |

**Relationship**: one `ExtractionOutcome` per processed asset per processing run; overwritten on
re-processing (idempotent per FR-013 — not appended/versioned).

---

## Entity Relationship Summary

```
Asset (existing) ──1:1── DocumentModel (per processing run)
DocumentModel ──1:N── StructuralElement (ordered)
StructuralElement ──0:1── parent StructuralElement (section/table hierarchy)
StructuralElement(s) ──N:1── Chunk (chunk_mapper grouping, N≥1 same-type adjacent elements)
Chunk (existing DataChunk) ── chunk_metadata.source_element_ids ──> StructuralElement.id (informational, not a DB FK)
Domain Pack (fields/{domain}/chunking.yaml) ──configures──> ElementChunkConfig ──drives──> chunk_mapper grouping per type
Asset.asset_config.extraction ── mirrors ── DocumentModel.extraction_outcome / degradation_reason
```
