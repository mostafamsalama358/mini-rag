# Data Model: Context Builder (spec 012)

**Module**: `src/core/context_builder/`
**Date**: 2026-07-14

All models are Pydantic v2 `BaseModel` unless noted. Domain models live in
`src/core/context_builder/models.py`; configuration models in `config.py`.

---

## Output Models (`models.py`)

### `Context`

Top-level output contract consumed by Answer Generation (spec 013).

```
Context
├── context_id: str               # "ctx_" + sha256(pack_id + created_at)[:16]
├── pack_id: str                  # EvidencePack.pack_id that produced this Context
├── plan_id: str                  # threaded through from EvidencePack.plan_id
├── schema_version: str           # "1.0.0" — bumped on breaking change
├── ordered_blocks: list[ContextBlock]    # text blocks in stitched order; may be empty
├── citation_map: dict[str, Citation]     # item_id → Citation; 1:1 with ordered_blocks
├── token_count: int              # sum of ContextBlock.token_count; ≤ budget
├── conflicts: list[ConflictGroup]        # empty if no conflicts detected
├── metadata: ContextMetadata
└── created_at: str               # ISO 8601 UTC
```

**Invariants**:
1. `set(b.item_id for b in ordered_blocks) == set(citation_map.keys())`
   (every block has a citation; every citation has a block).
2. `token_count == sum(b.token_count for b in ordered_blocks)`.
3. `token_count ≤ ContextBuilderConfig.available_budget` (computed at runtime).
4. `citation_map` is never `None`; empty dict when `ordered_blocks` is empty.

---

### `ContextBlock`

A single text unit in the assembled context, corresponding 1:1 to one `EvidenceItem`.

```
ContextBlock
├── item_id: str                  # EvidenceItem.item_id (non-empty)
├── document_id: str              # EvidenceItem.doc_id (non-empty)
├── section_path: str | None      # "/"-joined EvidenceItem.section_path; None if []
├── text: str                     # non-empty; may be compressed form
├── token_count: int              # token count of `text` (≥ 1)
└── compressed: bool              # True if IContextCompressor was applied
```

---

### `ConflictGroup`

Two or more items that contradict each other on the same entity attribute.

```
ConflictGroup
├── entity_tag: str               # matched entity_tag string (e.g., "metformin")
├── attribute: str                # heuristic attribute label (e.g., "metformin:numeric")
├── item_ids: list[str]           # ≥ 2 item_ids involved (non-empty)
└── resolution: str | None        # "budget_drop" if one item dropped for budget;
                                  # None if both items survive in Context
```

---

### `ContextMetadata`

Diagnostic payload attached to every `Context`.

```
ContextMetadata
├── items_included: int           # len(ordered_blocks)
├── items_dropped: int            # items from EvidencePack not in ordered_blocks
├── items_compressed: int         # ContextBlock.compressed == True count
├── conflicts_detected: bool      # len(conflicts) > 0
├── budget_total: int             # ITokenBudgetAllocator.available_budget
├── budget_used: int              # Context.token_count
└── timeout: bool                 # True if pipeline hit configurable timeout limit
```

---

## Configuration Model (`config.py`)

### `BudgetReservations`

```
BudgetReservations
├── system_prompt: int = 500      # tokens reserved for system prompt
├── question: int = 200           # tokens reserved for user question
└── output: int = 1000            # tokens reserved for model output
```

### `ContextBuilderConfig`

```
ContextBuilderConfig
├── total_context_window: int = 8000          # total model context window (tokens)
├── reservations: BudgetReservations          # default: system=500, question=200, output=1000
├── compressibility_threshold: float = 0.7   # items above this are compressed before drop
├── final_dedup_enabled: bool = True
├── final_dedup_similarity_threshold: float = 0.85   # Jaccard char-ngram threshold
├── final_dedup_max_pairs: int = 2000         # cap on O(n²) comparison pairs
├── compression_enabled: bool = True
├── compression_strategy: str = "heuristic"  # "heuristic" | "llm"
├── token_counter: str = "character"         # "character" | "tiktoken"
├── timeout_seconds: float = 30.0
├── evidence_pack_schema_version: str = "1.0.0"  # expected major version "1"
└── schema_version: str = "1.0.0"            # this config's own schema version
```

**Derived property** (computed, not stored):

```python
@property
def available_budget(self) -> int:
    return max(
        0,
        self.total_context_window
        - self.reservations.system_prompt
        - self.reservations.question
        - self.reservations.output,
    )
```

---

## Errors (`errors.py`)

```
ContextBuildError(Exception)           # base; all pipeline errors inherit from this
├── EvidencePackVersionError           # incompatible EvidencePack.schema_version major
├── EmptyBudgetError                   # available_budget ≤ 0 after reservations
└── CitationIntegrityError             # item_id in ordered_blocks missing from citation_map
```

---

## Reused Types (imported from spec 011 — not redefined)

| Type | Import path |
|------|-------------|
| `EvidencePack` | `core.evidence_orchestrator.models` |
| `EvidenceItem` | `core.evidence_orchestrator.models` |
| `Citation` | `core.evidence_orchestrator.models` |
| `ITokenCounter` | `core.evidence_orchestrator.interfaces` |
| `char_ngrams` | `core.evidence_orchestrator.text_similarity` |
| `jaccard_similarity` | `core.evidence_orchestrator.text_similarity` |

---

## Relationships

```
EvidencePack (spec 011 input)
    └── items: list[EvidenceItem]
                    │
                    ▼
         ContextBuilderPipeline
         [allocate → select → compress → detect → stitch → dedup → assemble]
                    │
                    ▼
              Context (output)
              ├── ordered_blocks: list[ContextBlock]   ← one per surviving EvidenceItem
              ├── citation_map: dict[item_id, Citation] ← Citation from EvidenceItem.citation
              ├── conflicts: list[ConflictGroup]
              └── metadata: ContextMetadata
```

---

## Config File Layout

```yaml
# src/fields/generic/context_builder.yaml  (generic baseline)
total_context_window: 8000
reservations:
  system_prompt: 500
  question: 200
  output: 1000
compressibility_threshold: 0.70
final_dedup_enabled: true
final_dedup_similarity_threshold: 0.85
final_dedup_max_pairs: 2000
compression_enabled: true
compression_strategy: heuristic
token_counter: character
timeout_seconds: 30.0
evidence_pack_schema_version: "1.0.0"
schema_version: "1.0.0"
```

Domain packs override specific keys only (e.g., pharmacy increases
`total_context_window: 16000` for larger clinical documents).
