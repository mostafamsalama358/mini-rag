# Contract: Document Model (internal core interface)

**Version**: 1.0.0 | **Feature**: `006-document-intelligence-pipeline`

This is an **internal library contract**, not an HTTP API: the seam between format parsers,
the chunk mapper, indexing tasks, and field resolution. Any code producing or consuming a
`DocumentModel` MUST conform to this contract. See `data-model.md` for full field definitions.

## Producer contract — `DocumentParser` protocol

Every format parser registered in `core/document_intelligence/parsers/` MUST implement:

```python
class DocumentParser(Protocol):
    def parse(self, file_path: str, file_id: str) -> "DocumentModel":
        """Parse one file into a DocumentModel.

        MUST NOT raise for content-shape issues it can degrade gracefully from
        (empty content, unsupported inner structure) — instead raise
        DocumentIntelligenceDegraded(reason=...) so the caller can build the
        fallback model (see Fallback contract below).

        MUST raise a normal exception (not DocumentIntelligenceDegraded) when
        the file cannot be opened/read at all — this is a hard failure per FR-011.
        """
```

**Registration**: `ParserRegistry.register(extension: str, parser: DocumentParser)`;
`get_parser_for_extension(ext: str) -> DocumentParser | None`. No caller branches on
extension directly outside the registry (research R2).

## Structural element vocabulary (frozen for v1, extensible per FR-001a)

```
section | paragraph | table | table-row | list | list-item
```

- Consumers (chunk mapper, field resolution, citation formatting) MUST treat unknown future
  element types they don't explicitly handle by falling back to their `paragraph`-equivalent
  handling (forward compatibility) rather than raising.
- Producers MUST NOT invent ad hoc types outside this vocabulary without a spec amendment
  (FR-001a).

## Fallback contract (degraded extraction)

```python
class DocumentIntelligenceDegraded(Exception):
    reason: Literal["unsupported_structure", "parse_error", "empty_content"]
```

When a parser raises this, the caller (`services/process_service.py`) MUST construct:

```python
DocumentModel(
    asset_id=...,
    source_format=...,
    elements=[StructuralElement(type="section", text=<best-effort whole text>, ...)]
             if best_effort_text else [],
    extraction_outcome="degraded",
    degradation_reason=exc.reason,
)
```

and processing MUST continue (chunking + indexing proceed on the degraded model) — this is
the FR-011 guarantee.

## Chunk mapper contract

```python
def map_elements_to_chunks(
    elements: list[StructuralElement],
    config: dict[str, ElementChunkConfig],  # keyed by canonical element type
) -> list[Chunk]:
    """
    Invariants (MUST hold for every call):
      1. No StructuralElement is split across two returned chunks, UNLESS a single
         element's rendered size exceeds config[element.type].max_chunk_chars, in
         which case that one oversized element MAY be internally split (documented
         exception, FR-005).
      2. Every returned chunk's chunk_metadata["source_element_ids"] is a non-empty
         list of the id(s) of the element(s) it was derived from.
      3. Grouping two adjacent elements into one chunk is only valid when both are
         the same canonical type AND config[type].group is True.
      4. Output chunk order matches input element order (stable, no reordering).
    """
```

## Consumer expectations

- **Field resolution** (`core/field_resolution.py`): continues to read `table-row` chunk
  metadata's `fields` mapping unchanged — this feature does not alter the `FieldManifest`
  discovery contract, only how `fields`-bearing chunks are produced upstream.
- **Citations** (`utils/chunk_metadata.format_source_label`): reads `chunk_metadata` plus,
  when set, the pack's `MetadataProfile.label_template` — see
  `element-mapping-yaml-contract.md` for the template contract.
- **Observability** (`utils/metrics.py`, task logs): every ingestion run MUST log
  `DocumentModel.extraction_outcome`, `degradation_reason` (if any), and per-type element
  counts (NFR-007) — this is the same payload persisted to `asset_config.extraction`
  (see `data-model.md` §6).
