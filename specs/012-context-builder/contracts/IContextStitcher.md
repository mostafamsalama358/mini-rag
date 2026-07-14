# Contract: `IContextStitcher`

**Module**: `src/core/context_builder/interfaces.py`
**Consumer**: `ContextBuilderPipeline` (stage 5 — Section Stitching / Ordering)

## Purpose

Orders a list of surviving `EvidenceItem` objects into a coherent document-structure
sequence and converts them into `ContextBlock` objects. The resulting list is the
`Context.ordered_blocks` field consumed by Answer Generation.

## Interface

```python
class IContextStitcher(ABC):
    @abstractmethod
    async def stitch(
        self,
        items: list[EvidenceItem],
        token_counter: ITokenCounter,
    ) -> list[ContextBlock]:
        """
        Order items by document structure and emit ContextBlock objects.

        Returns:
            Ordered list of ContextBlock; empty list when items is empty.

        Guarantees:
            - Every input EvidenceItem produces exactly one ContextBlock.
            - len(result) == len(items).
            - ContextBlock.item_id == EvidenceItem.item_id.
            - ContextBlock.compressed is False (compression was already applied
              upstream; stitcher receives the final text).
            - ContextBlock.token_count is computed by token_counter.count_tokens(text).
        """
```

## Contract Rules

1. `len(result) == len(items)` — every item becomes exactly one block; no items are
   dropped or duplicated by the stitcher.
2. `result[i].item_id` MUST equal the `item_id` of the item it was produced from.
3. `result[i].compressed` MUST reflect whether the item's text was already compressed
   upstream (passed through from the selection stage, not re-set by the stitcher).
4. `ContextBlock.section_path` is the `"/"`-joined form of `EvidenceItem.section_path`;
   `None` when `EvidenceItem.section_path == []`.
5. MUST NOT mutate input `items`.

## Default Implementation

`SectionPathStitcher` in `src/core/context_builder/stitching/section_path_stitcher.py`

### Ordering Algorithm

Sort items by `(document_id, section_path_list, -relevance_score)` where:
- `document_id`: string sort — all blocks from the same document appear consecutively.
- `section_path_list`: `EvidenceItem.section_path` (`list[str]`) — Python's default
  lexicographic list comparison; `["Introduction"]` < `["Introduction", "Background"]`
  (depth-first, then alphabetically within a level).
- Items with `section_path == []` sort after items with a non-empty path within the
  same document.
- Items with no `document_id` (`""`) are grouped at the end, then sorted by
  `-relevance_score`.
- Within identical `(document_id, section_path)`, higher `relevance_score` leads.

### `section_path` Flattening

```python
block.section_path = "/".join(item.section_path) or None
```

### `ContextBlock` Construction

```python
ContextBlock(
    item_id=item.item_id,
    document_id=item.doc_id,
    section_path="/".join(item.section_path) or None,
    text=item.text,               # text is already the final (possibly compressed) form
    token_count=token_counter.count_tokens(item.text),
    compressed=item_was_compressed,  # boolean passed from selection stage
)
```

## Extension Points

Alternative implementations may:
- Group items by semantic cluster rather than document hierarchy.
- Interleave documents by alternating relevance (round-robin across documents).
- Apply domain-specific section ordering rules (e.g., always put "Summary" sections
  first in legal documents).
