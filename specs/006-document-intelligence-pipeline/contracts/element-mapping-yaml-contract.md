# Contract: `element_mapping` YAML Schema (domain pack authoring contract)

**Version**: 1.0.0 | **Feature**: `006-document-intelligence-pipeline`

This is the declarative contract domain-pack authors use to change chunking/citation behavior
**without touching core code** (FR-009/FR-010, US3). It extends `fields/{domain}/chunking.yaml`.

## Schema

```yaml
# fields/{domain}/chunking.yaml
by_extension:            # UNCHANGED — selects parser per raw format, not per domain behavior
  .xlsx: xlsx
  .csv: csv
  .pdf: pdf
  .txt: txt

default_strategy: xlsx   # parser fallback when extension not in by_extension

chunk_size: 800           # generic default character budget (existing field, unchanged)
overlap: 120               # generic default overlap (existing field, unchanged; applies to
                            # oversized-element internal splitting only — see FR-005 exception)

element_mapping:          # NEW — per canonical element type (FR-001a vocabulary only)
  table-row:
    group: false           # never combine two table-row elements into one chunk
    max_chunk_chars: 2000
    metadata_keys: [sheet_name, row_index]
  paragraph:
    group: true             # adjacent paragraphs may share a chunk
    max_chunk_chars: 800
  list-item:
    group: true
    max_chunk_chars: 500
  section:
    group: false
  table:
    group: false
```

## Field rules

| Field | Required | Type | Rule |
| ----- | -------- | ---- | ---- |
| `element_mapping` | no | `dict[str, ElementChunkConfig]` | Absent keys inherit generic pack defaults (precedence: generic < domain < project config, unchanged from existing `FieldRegistry` merge order). |
| `element_mapping.<type>` key | — | must be one of the canonical vocabulary (`section`, `paragraph`, `table`, `table-row`, `list`, `list-item`) or a spec-amendment-approved extension type | Unknown keys are ignored with a startup warning (fail-fast in production per Constitution error-handling convention for invalid packs), never silently mis-mapped. |
| `group` | no (default varies by type, see `data-model.md` §3) | `bool` | `false` MUST be used for any element type where splitting/merging would corrupt meaning (e.g., `table-row`). |
| `max_chunk_chars` | no (defaults to `chunk_size`) | `int > 0` | Governs both the grouping budget and the oversized-element-split threshold (FR-005 exception). |
| `metadata_keys` | no (default `[]`) | `list[str]` | Keys from `StructuralElement.provenance`/`fields` to copy into `chunk_metadata` beyond the always-present base keys (`file_name`, `asset_id`, `chunk_order`, `char_count`, `element_type`, `source_element_ids`). |

## Citation label contract (`chunk_metadata.yaml`, unchanged file — wiring completed by this feature)

```yaml
# fields/{domain}/chunk_metadata.yaml
label_template: "{file_name} — row {row_index}"   # already existed; now actually consumed
extra_keys: [file_name, row_index, sheet_name]
```

`label_template` uses `str.format`-style placeholders resolved against the chunk's
`chunk_metadata` (which now includes any `metadata_keys` declared above). No Python
per-domain formatting function is permitted (FR-015) — a domain that needs a new
placeholder adds it to `metadata_keys` + `label_template`, nothing else.

## Backward-compatibility rule

A pack that ships **no** `element_mapping` block MUST behave identically to its current
`by_extension` strategy behavior (research R6 migration guarantee) — e.g., pharmacy's XLSX
`row` strategy today is exactly `element_mapping.table-row: {group: false}` applied
generically, not a new behavior.

## Example: adding a new domain (US3 acceptance test)

Adding a "manuals" domain that wants short list items grouped into bigger chunks (unlike
pharmacy's ungrouped rows) requires **only**:

```yaml
# fields/manuals/chunking.yaml
element_mapping:
  list-item:
    group: true
    max_chunk_chars: 1500
```

No file under `src/core/document_intelligence/` changes — satisfies SC-002.
