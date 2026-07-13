# Research: Intelligent Chunking Engine

**Feature**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13
**Phase**: 0 — Pre-design research

---

## R1: Boundary Decision Policy — Rule Precedence

**Decision**: The default `RuleBasedBoundaryDecisionPolicy` applies signals in strict priority order:

1. **Structural integrity (absolute)**  — `table_integrity=false`, `code_integrity=false`, or `quote_integrity=false` → `split` (these types must never be fragmented; no other signal can override)
2. **Section / heading boundary** — `section_continuity=false` → `split`; `heading_continuity=false` when combined size is within budget → `split` (an orphaned heading is worse than a small chunk)
3. **Hierarchy breach** — `hierarchy_continuity=false` → `split` (elements from different structural ancestors must not merge)
4. **Size budget** — `size_budget=over_limit` → `split` (only reached if none of the above fired; an element already over limit alone triggers the oversized-element fallback in the Chunk Builder, not here)
5. **Structural incompatibility** — `structural_compatibility=false` → `split` (e.g., `table-row` adjacent to `paragraph`)
6. **Layout / lexical continuity** — if both are `false` → `split`; if only one → `split` for stricter modes (configurable threshold)
7. **Default** → `merge` (all signals pass; accumulate into current chunk)

**Rationale**: Semantic integrity (never break atomic blocks) comes first, then structural context (sections/headings), then size constraints. This is deterministic with no tie-breaking randomness. Any alternative policy can override all seven levels by implementing the `BoundaryDecisionPolicy` interface.

**Alternatives considered**:
- Weighted scoring (all signals summed with learned weights) — rejected: non-deterministic unless frozen, opaque to debugging, reserved for future optional policy
- Single threshold on number of `true` signals — rejected: cannot guarantee absolute structural integrity

---

## R2: Stable Chunk Identity Algorithm

**Decision**: `chunk_id = "ck_" + SHA256("{asset_id}|{sorted_element_ids}|{strategy_id}|{config_hash}")[:16]`

Where:
- `asset_id` — `DocumentModel.asset_id` (string cast)
- `sorted_element_ids` — sorted `StructuralElement.id` list joined by `,` (sort guarantees stability regardless of merge accumulation order)
- `strategy_id` — registered strategy name string (e.g., `"semantic_structural"`)
- `config_hash` — SHA256 of the strategy's serialized config dict (max_chars, policy name, etc.), first 8 hex chars

**Format**: `ck_a3f9b1c2d4e5f678` (prefix `ck_` + 16 hex chars from SHA256)

**Rationale**: Same input + same config → same id (FR-008/FR-014). The sort on element ids means adding an element to a group changes the id (correct — different semantic unit). Config-fingerprint inclusion means changing chunking parameters intentionally produces new ids, preventing stale retrieval of semantically-different chunks.

**Alternatives considered**:
- UUID v5 (namespace + name) — equivalent collision properties, but SHA256 with explicit inputs is more auditable
- Sequential integer — not stable across re-processing; rejected

---

## R3: Additive Chunk Metadata Storage

**Decision**: Extend `chunk_metadata` JSONB with these new additive keys (no DB schema change):

| Key | Type | Purpose |
|-----|------|---------|
| `chunk_id` | `str` | Stable identity (FR-008) |
| `parent_chunk_id` | `str \| null` | Parent grouping chunk (FR-010) |
| `previous_chunk_id` | `str \| null` | Reading-order predecessor (FR-011) |
| `next_chunk_id` | `str \| null` | Reading-order successor (FR-011) |
| `heading_path` | `list[str]` | Enclosing heading/section titles (FR-009) |
| `chunk_position` | `int` | 0-based position in document (FR-009) |
| `lineage` | `dict` | `{source_element_ids, applied_rule, triggered_features, rationale}` (FR-013) |
| `boundary_decision` | `dict` | `{applied_rule, triggered_features, rationale}` for the closing boundary |

The `ValidationReport` is **not** stored per-chunk; it is returned in-memory as part of `ChunkSet` and optionally logged at the Celery task boundary (NFR-007). It can be re-produced by re-running validation on the stored chunks.

Existing keys (`file_name`, `asset_id`, `chunk_order`, `char_count`, `page`, `sheet_name`, `row_index`, `fields`, `col_*`, `source_element_ids`, `element_type`) remain unchanged (FR-031/FR-032).

**Rationale**: Mirrors `006`'s additive approach (added `source_element_ids`/`element_type` without schema change). JSONB is already the persistence contract; no migration required.

---

## R4: StructuralElementType Vocabulary Extension

**Decision**: Extend the `StructuralElementType = Literal[...]` type union and `CANONICAL_ELEMENT_TYPES` frozenset in `core/document_intelligence/model.py`:

```python
StructuralElementType = Literal[
    # existing six (unchanged)
    "section", "paragraph", "table", "table-row", "list", "list-item",
    # new four (FR-004)
    "heading", "code-block", "quote", "figure-placeholder",
]
```

`ConfigDict(extra="forbid")` on `StructuralElement` already guards against typos. The `model_validator` text/fields rule extends naturally: `figure-placeholder` uses `text` (possibly empty string); `code-block`, `quote`, `heading` use `text`.

Forward-compat fallback (FR-005): the new chunking engine's `_config_for` falls back to paragraph-equivalent config for any type not in the active strategy's element_mapping — exactly as the current `_DEFAULT_GROUP` dict does in `chunk_mapper.py`.

Parser retrofit is explicitly out of scope (spec §Out of Scope); parsers that never emit the new types continue to work unchanged.

**Rationale**: Smallest possible change to the existing model; all four new types follow the same text/fields invariant. Existing callers that iterate `element.type` as a string continue to work.

---

## R5: Performance Baseline & SC-008 Threshold

**Decision**: Establish baseline in the first integration test milestone by:
1. Running `map_elements_to_chunks` on a 50-document fixture set, recording per-document wall-clock time (median, p95)
2. Documenting result in `tests/integration/benchmarks/chunking_baseline.json`
3. SC-008 threshold: new engine ≤ **2×** current baseline median (conservative; the new engine has O(N) boundary evaluations vs O(N) element scans, but each evaluation is more work)

**Rationale**: 2× threshold allows semantic richness overhead while staying well within Celery task timeout headroom. If benchmarks show tighter feasibility, threshold is tightened during implementation.

---

## R6: Strategy Registry Pattern

**Decision**: A module-level dict registry with explicit register/get functions, mirroring `utils/rerank/factory.py::get_reranker()`:

```python
# core/chunking/registry.py
_REGISTRY: dict[str, type[ChunkingStrategy]] = {}

def register_strategy(name: str, cls: type[ChunkingStrategy]) -> None: ...
def get_chunking_strategy(name: str, config: ChunkingStrategyConfig) -> ChunkingStrategy: ...
```

Strategies self-register at module import time. The `ChunkingProfile.strategy` (new YAML key, default `"semantic_structural"`) drives selection. The factory raises `KeyError` for unknown names (loud failure > silent fallback to wrong strategy).

**Alternatives considered**:
- Entry points / setuptools plugin system — overkill for an in-process registry; rejected
- Conditional if/elif in caller — explicitly rejected (constitution Principle V; NFR-002)

---

## R7: Oversized Single-Element Handling in Chunk Builder

**Decision**: The Chunk Builder handles oversized single elements directly, as a documented exception:

1. When the Chunk Builder closes a chunk containing exactly **one** structural element whose rendered text exceeds `max_chars`, it invokes an internal `_OversizedSplitter` helper (not a `BoundaryDecisionPolicy`).
2. The `_OversizedSplitter` splits at the best available sub-boundary: paragraph break → sentence boundary (`.`/`?`/`!`) → raw character cut.
3. Each resulting sub-chunk is emitted with:
   - `lineage.applied_rule = "oversized_element_fallback"`
   - `lineage.triggered_features = ["size_budget"]`
   - `metadata.oversized_split_index = <n>`
4. Every sub-chunk carries the full structural context (heading_path, etc.) of the original element.

**Why not route through BoundaryDecisionPolicy?**: There is no boundary between two elements — the problem is a single element that exceeds the limit on its own. Routing through the Policy would require fabricating a BoundaryCandidate, creating misleading lineage. The Chunk Builder's existing responsibility (assembling chunks) naturally includes this documented exception case (FR-018 / FR-021).

**Rationale**: Consistent with existing `_split_oversized` behavior in `chunk_mapper.py`. Explicitly records the exception in lineage as required by FR-018. Keeps BoundaryDecisionPolicy free of oversized-element special-casing.

---

## R8: BoundaryFeatures Signal Computation Details

| Signal | How computed |
|--------|-------------|
| `hierarchy_continuity` | `left.parent_id == right.parent_id` (same enclosing section/table) |
| `heading_continuity` | right element is not a `heading`/`section` type, OR left is a `heading` whose `parent_id` matches right's `parent_id` |
| `section_continuity` | both elements share the same nearest `section`/`heading` ancestor in the element tree |
| `structural_compatibility` | element types appear in the same compatibility group (see below) |
| `lexical_continuity` | `True` by default (no NLP required); `False` only when types are fundamentally incompatible (e.g., `code-block` after `paragraph`) — rule-based, not probabilistic |
| `table_integrity` | neither element is `table-row` with a different `sheet_name`/table parent than the other |
| `list_integrity` | neither element is `list-item` with a different list `parent_id` |
| `code_integrity` | neither element is `code-block` being merged with a non-`code-block` element |
| `quote_integrity` | neither element is `quote` being merged with a non-`quote` element |
| `layout_continuity` | `True` if both elements have compatible `page` provenance (same page or adjacent pages); `True` for formats without page provenance |
| `size_budget` | `within_limit` if `len(accumulated_text + sep + right_text) <= max_chars`; `over_limit` otherwise |

**Compatibility groups** (for `structural_compatibility`):
- Group A: `paragraph`, `heading`, `section`, `list`, `list-item`, `quote` — prose/structured text
- Group B: `table`, `table-row` — tabular content
- Group C: `code-block` — code content
- Group D: `figure-placeholder` — figure/media references

Elements from different groups are structurally incompatible → `structural_compatibility = False`.

---

## R9: ChunkBuilder Lifecycle & Parent/Child Hierarchy

**Decision**: The Chunk Builder maintains two data structures:
1. `_open_chunk`: the currently-accumulating (not-yet-closed) chunk state
2. `_heading_stack: list[str]`: a stack of heading/section element ids representing the current heading path — updated whenever a `heading` or `section` element is appended

Parent/child relationship:
- A `section`-level chunk (one whose primary element is `section` or `heading`) is treated as a **parent** of the paragraph/list/table chunks that follow under it.
- The Chunk Builder tracks `_current_section_chunk_id` (the last closed section-level chunk id) and assigns it as `parent_chunk_id` for all subordinate chunks until a new section begins.
- Leaf chunks (paragraph, table-row, list-item, code-block, etc.) → `child_chunk_ids = []`

Previous/next links: assigned after all chunks for the document are closed, in a single post-processing pass over the ordered chunk list (avoids circular forward-reference resolution).

**Rationale**: This two-pass approach (open/append/close → link) satisfies FR-047 (identity before relationships) while keeping the Chunk Builder stateful but O(N) total.
