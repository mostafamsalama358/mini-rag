# Contract: `IConflictDetector`

**Module**: `src/core/context_builder/interfaces.py`
**Consumer**: `ContextBuilderPipeline` (stage 4 — Conflict Detection)

## Purpose

Identifies pairs (or groups) of `EvidenceItem` objects that contradict each other on
the same entity. Returns a list of `ConflictGroup` objects that are attached to the
final `Context.conflicts` field so Answer Generation can disclose disagreement.

## Interface

```python
class IConflictDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        items: list[EvidenceItem],
        config: ContextBuilderConfig,
    ) -> list[ConflictGroup]:
        """
        Scan items for conflicting evidence about the same entity.

        Returns:
            List of ConflictGroup; empty list if no conflicts found.

        Guarantees:
            - Each ConflictGroup.item_ids contains ≥ 2 item_ids.
            - All item_ids in a ConflictGroup are present in the input `items` list.
            - No item_id appears in more than one ConflictGroup for the same
              entity_tag (groups are merged when three+ items conflict on the same tag).
            - On failure, returns [] and logs a structured warning; never raises.
        """
```

## Contract Rules

1. MUST return `[]` (not raise) on error; a failed conflict scan is not a pipeline
   blocker.
2. All `item_ids` in returned `ConflictGroup` objects MUST be present in the input
   `items` list.
3. `ConflictGroup.item_ids` MUST contain ≥ 2 entries.
4. MUST NOT mutate the input `items` list.

## Default Implementation

`EntityTagConflictDetector` in `src/core/context_builder/conflict/entity_tag_detector.py`

### Algorithm (no upstream schema change required)

**Data source**: `EvidenceItem.entity_tags: list[str]` — canonical entity forms
populated by Evidence Orchestrator from spec 008 KnowledgeUnit tags.

**Step 1 — Grouping**: Build an inverted index `{entity_tag → list[EvidenceItem]}`.
Items that share at least one entity_tag are candidate conflict pairs.

**Step 2 — Value extraction**: For each candidate group, apply a regex over
`EvidenceItem.text` to extract numeric tokens within a configurable character window
(default: 100 chars) of the entity tag mention. Extract categorical tokens (boolean-
like or enumerated strings) in the same window.

**Step 3 — Comparison**: If two items in the group have different numeric values for
the same entity tag context (differing by more than a configurable absolute tolerance,
default 0.0), emit a `ConflictGroup` with:
  - `entity_tag`: the shared entity tag string
  - `attribute`: `"{entity_tag}:numeric"` for numeric conflicts,
    `"{entity_tag}:categorical"` for categorical conflicts
  - `item_ids`: all item_ids sharing the conflicting tag
  - `resolution`: `None` (budget-drop resolution is set by the pipeline, not the detector)

**Step 4 — Deduplication**: Merge conflict groups that share the same `entity_tag`
and `attribute` (e.g., three items all conflicting on `"metformin:numeric"` form a
single group, not three pairs).

### Why no upstream schema change is needed

`entity_tags: list[str]` on `EvidenceItem` already carries canonical entity identifiers
from spec 008 KnowledgeUnit tags. The detector derives grouping keys from these strings
directly. The `attribute` label is a heuristic suffix (`:numeric` / `:categorical`) —
it does not require a structured attribute-value field on `EvidenceItem`.

## Extension Points

Alternative implementations may use:
- Embedding-based semantic contradiction detection (requires `IEmbeddingProvider`).
- LLM-based entailment scoring.
- Structured entity-attribute matching if spec 011 adds attribute-value pairs to
  `entity_tags` in a future minor version.
