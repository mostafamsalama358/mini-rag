# Contract: ChunkingStrategy Interface

**Feature**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13

This contract defines the stable interface that every chunking strategy implementation must
satisfy. Code that calls the chunking engine (e.g., Celery tasks in `tasks/file_processing.py`)
depends only on this contract, never on a concrete strategy class.

---

## Interface Definition

**Location**: `src/core/chunking/interfaces.py`

```python
from abc import ABC, abstractmethod
from core.document_intelligence.model import DocumentModel
from core.chunking.models import ChunkSet, ChunkingStrategyConfig

class ChunkingStrategy(ABC):
    """Stable interface for every chunking strategy implementation.

    Implementors:
    - Receive a DocumentModel (from 006) as sole input; MUST NOT access raw files.
    - MUST be deterministic: same input + same config → same ChunkSet every time.
    - MUST NOT introduce embeddings, LLM calls, or blocking I/O.
    - MUST register via `core.chunking.registry.register_strategy(name, cls)`.
    """

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique registered name for this strategy (e.g., 'semantic_structural')."""
        ...

    @abstractmethod
    def chunk(
        self,
        document_model: DocumentModel,
        config: ChunkingStrategyConfig,
    ) -> ChunkSet:
        """Produce a validated ChunkSet from the given DocumentModel.

        Args:
            document_model: The Canonical Document Model produced by 006.
            config: Strategy configuration (max_chars, policy, element_mapping, ...).

        Returns:
            ChunkSet containing ordered Chunks and a ValidationReport.
            The ValidationReport is always present; status may be 'pass', 'fail',
            or 'pass_with_warnings'.

        Raises:
            ChunkingError: For unrecoverable input errors (empty document model
                           with no elements is not an error — returns empty ChunkSet).
        """
        ...
```

---

## Registration Contract

**Location**: `src/core/chunking/registry.py`

```python
def register_strategy(name: str, cls: type[ChunkingStrategy]) -> None:
    """Register a strategy class under the given name.

    Call at module import time so the strategy is available when the factory is invoked.
    Raises ValueError if 'name' is already registered with a different class.
    """

def get_chunking_strategy(
    name: str,
    config: ChunkingStrategyConfig,
) -> ChunkingStrategy:
    """Instantiate and return the strategy registered under 'name'.

    Raises KeyError if name is not registered (loud failure; no silent fallback).
    """
```

---

## ChunkingStrategyConfig Schema

**Location**: `src/core/chunking/models.py`

| Field | Type | Default | Source |
|---|---|---|---|
| `strategy` | `str` | `"semantic_structural"` | `ChunkingProfile.strategy` (YAML pack) |
| `max_chars` | `int` | `800` | `ChunkingProfile.chunk_size` |
| `overlap` | `int` | `0` | `ChunkingProfile.overlap` |
| `policy` | `str` | `"rule_based"` | `ChunkingProfile.policy` (YAML pack, new key) |
| `element_mapping` | `dict[str, ElementChunkConfig]` | `{}` | `ChunkingProfile.element_mapping` |

---

## YAML Pack Extension

Pack YAML (`fields/{domain}/chunking.yaml`) gains one new optional key:

```yaml
strategy: semantic_structural    # new — selects ChunkingStrategy implementation
policy: rule_based               # new — selects BoundaryDecisionPolicy
chunk_size: 800
overlap: 0
element_mapping:
  paragraph:
    group: true
  # ... existing keys unchanged
```

Packs that omit `strategy` and `policy` receive the defaults (`semantic_structural` /
`rule_based`). The existing `by_extension` key is unchanged (selects parser, not chunker).

---

## ChunkSet Output Contract

Every `ChunkingStrategy.chunk()` call returns a `ChunkSet` whose `chunks` list contains
backward-compatible `{"text": str, "metadata": dict}` records augmented with rich fields.

**Mandatory `chunk.metadata` keys** (backward-compatible, never removed):

| Key | Notes |
|---|---|
| `element_type` | Canonical element type (populated since `006`) |
| `source_element_ids` | Source `StructuralElement.id` list (populated since `006`) |
| `char_count` | Length of `text` |
| `file_name` | Asset file name (when present in provenance) |
| `page` | Page number (for PDF assets; from provenance) |
| `sheet_name` | Sheet name (for XLSX assets; from provenance) |
| `row_index` | Row index (for tabular assets; from provenance) |
| `fields` | Column-value dict (for `table-row` elements) |
| `col_*` | Individual column keys (for `table-row` elements) |

**New additive `chunk.metadata` keys** (this feature):

| Key | Notes |
|---|---|
| `chunk_id` | Stable deterministic identity (FR-008) |
| `parent_chunk_id` | Enclosing section chunk id, or `null` |
| `previous_chunk_id` | Reading-order predecessor id, or `null` |
| `next_chunk_id` | Reading-order successor id, or `null` |
| `heading_path` | List of enclosing heading/section titles |
| `chunk_position` | 0-based document-order position |
| `lineage` | Dict: `{source_element_ids, applied_rule, triggered_features, rationale}` |

---

## Invariants (enforced by the engine, not by callers)

1. `ChunkSet.validation_report` is always populated before the set is returned.
2. No chunk in `ChunkSet.chunks` has been mutated after `ChunkValidator` ran.
3. `chunk_id` values within a `ChunkSet` are unique.
4. All `parent_chunk_id`, `previous_chunk_id`, `next_chunk_id` references resolve to actual chunk ids within the same `ChunkSet`.
5. A `ChunkingStrategy` implementation that violates determinism is a contract breach.
