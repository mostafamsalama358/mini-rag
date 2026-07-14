# Contract: `Context` — Output Schema

**Module**: `src/core/context_builder/models.py`
**Schema version**: `1.0.0`
**Producer**: spec 012 (Context Builder)
**Consumer**: spec 013 (Answer Generation)

## Purpose

`Context` is the stable public output contract of the Context Builder. It carries an
ordered, token-budget-compliant list of text blocks, a 1:1 citation map, detected
conflict groups, and pipeline metadata. Spec 013 (Answer Generation) consumes `Context`
directly — it MUST NOT need to inspect the original `EvidencePack`.

## Schema

```
Context
├── context_id: str               # "ctx_" + sha256(pack_id + created_at)[:16]
├── pack_id: str                  # source EvidencePack.pack_id (non-empty)
├── plan_id: str                  # source EvidencePack.plan_id (non-empty)
├── schema_version: str           # "1.0.0" — pinned; bump on breaking change
├── ordered_blocks: list[ContextBlock]    # text blocks; order is stitching order
├── citation_map: dict[str, Citation]     # item_id → Citation; always populated
├── token_count: int              # sum of ContextBlock.token_count; ≤ budget
├── conflicts: list[ConflictGroup]        # empty list if none detected
├── metadata: ContextMetadata
└── created_at: str               # ISO 8601 UTC

ContextBlock
├── item_id: str                  # EvidenceItem.item_id (non-empty)
├── document_id: str              # EvidenceItem.doc_id (non-empty)
├── section_path: str | None      # "/"-joined heading path; None when original is []
├── text: str                     # non-empty; compressed form if compressed=True
├── token_count: int              # token count of text field (≥ 1)
└── compressed: bool              # True if IContextCompressor was applied to this item

ConflictGroup
├── entity_tag: str               # matched entity_tags entry (e.g., "metformin")
├── attribute: str                # heuristic attribute label (e.g., "metformin:numeric")
├── item_ids: list[str]           # ≥ 2 item_ids involved
└── resolution: str | None        # "budget_drop" | None

ContextMetadata
├── items_included: int           # len(ordered_blocks)
├── items_dropped: int            # items present in EvidencePack but not in Context
├── items_compressed: int         # blocks where compressed=True
├── conflicts_detected: bool      # len(conflicts) > 0
├── budget_total: int             # available_budget from ITokenBudgetAllocator
├── budget_used: int              # equals token_count
└── timeout: bool                 # True if pipeline hit timeout_seconds limit
```

## Invariants

1. `set(b.item_id for b in ordered_blocks) == set(citation_map.keys())`
   — enforced by Pydantic model validator; violated construction raises `CitationIntegrityError`.
2. `token_count == sum(b.token_count for b in ordered_blocks)`.
3. `token_count ≤ metadata.budget_total`.
4. `metadata.budget_used == token_count`.
5. `ordered_blocks` may be empty (when `EvidencePack.is_empty` or budget = 0);
   in that case `citation_map` is `{}` and `token_count` is `0`.
6. No two `ContextBlock` entries share the same `item_id`.

## Empty-Result Guarantee

When the input `EvidencePack.is_empty` is `True` or `available_budget` is 0, Context
Builder returns:

```python
Context(
    context_id="ctx_...",
    pack_id=pack.pack_id,
    plan_id=pack.plan_id,
    schema_version="1.0.0",
    ordered_blocks=[],
    citation_map={},
    token_count=0,
    conflicts=[],
    metadata=ContextMetadata(
        items_included=0,
        items_dropped=len(pack.items),
        items_compressed=0,
        conflicts_detected=False,
        budget_total=available_budget,
        budget_used=0,
        timeout=False,
    ),
    created_at="...",
)
```

No exception is raised; the caller (spec 013) checks `len(ordered_blocks) == 0`.

## Versioning Policy

- **PATCH** (1.0.x): docstring / description changes only.
- **MINOR** (1.x.0): new optional fields added; backwards-compatible.
- **MAJOR** (x.0.0): existing field removed or type changed; requires spec 013 migration.
- `schema_version` is checked by spec 013 at runtime; incompatible major version must
  raise a version error in 013.
