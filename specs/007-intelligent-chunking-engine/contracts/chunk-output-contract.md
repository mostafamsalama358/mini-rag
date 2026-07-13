# Contract: Chunk Output & Downstream Compatibility

**Feature**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13

This contract defines the output shape that the Intelligent Chunking Engine produces and the
backward-compatibility guarantees that downstream consumers (indexing, retrieval, storage) rely
on. No downstream change is required to consume output from this engine (FR-031/FR-032).

---

## Existing Contract (unchanged)

The existing `{"text": str, "metadata": dict}` record shape produced by `map_elements_to_chunks`
is fully preserved. Every key listed below continues to be populated identically.

| `metadata` key | Type | Consumer |
|---|---|---|
| `element_type` | `str` | Field resolution, citation logic |
| `source_element_ids` | `list[str]` | Provenance tracing (added by `006`) |
| `char_count` | `int` | Retrieval scoring |
| `file_name` | `str \| None` | Citation display |
| `page` | `int \| None` | PDF citation |
| `sheet_name` | `str \| None` | XLSX citation |
| `row_index` | `int \| None` | XLSX/CSV citation |
| `fields` | `dict \| None` | Table-row field lookup |
| `col_*` | `str` | Table-row column access |
| `oversized_split_index` | `int \| None` | Oversized fragment tracking (preserved from `007` fallback) |

---

## New Additive Keys (this feature)

These keys are added to every chunk's `metadata` dict. Consumers that do not yet read them
are unaffected. No existing key is renamed or removed.

| `metadata` key | Type | Required | Notes |
|---|---|---|---|
| `chunk_id` | `str` | yes | Stable identity; format `ck_{16 hex chars}` |
| `parent_chunk_id` | `str \| null` | yes | `null` for top-level / section chunks |
| `previous_chunk_id` | `str \| null` | yes | `null` for the first chunk in a document |
| `next_chunk_id` | `str \| null` | yes | `null` for the last chunk in a document |
| `heading_path` | `list[str]` | yes | Empty list when no heading context exists |
| `chunk_position` | `int` | yes | 0-based document-order index |
| `lineage` | `dict` | yes | `{source_element_ids, applied_rule, triggered_features, rationale, oversized_split_index}` |

---

## ValidationReport Availability

`ValidationReport` is returned in-memory as `ChunkSet.validation_report` and is NOT stored as
a `metadata` key on individual chunks. It is logged at the Celery task boundary (NFR-007).

Callers that need to re-inspect the report must re-run `ChunkValidator` against the stored chunks
(all required fields are available from stored metadata).

---

## How Downstream Callers Migrate

`tasks/file_processing.py` replaces the `map_elements_to_chunks` call site with:

```python
from core.chunking.registry import get_chunking_strategy
from core.chunking.models import ChunkingStrategyConfig

strategy = get_chunking_strategy(
    name=chunking_profile.strategy,
    config=ChunkingStrategyConfig(
        strategy=chunking_profile.strategy,
        max_chars=chunking_profile.chunk_size,
        overlap=chunking_profile.overlap,
        policy=chunking_profile.policy,
        element_mapping=chunking_profile.element_mapping,
    ),
)
chunk_set = strategy.chunk(document_model, config)
records = [{"text": c.text, "metadata": c.metadata} for c in chunk_set.chunks]
```

`records` is identical in shape to the previous `map_elements_to_chunks` output, with additive
metadata keys. All downstream indexing/retrieval/storage code receives the same `text`/`metadata`
structure it always has.

---

## Compatibility Smoke Test

See `quickstart.md §4` for the step-by-step command to verify zero diffs in indexing,
retrieval, and storage code paths when switching strategies (SC-004 / SC-010).
