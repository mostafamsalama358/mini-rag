# Data Model: Intelligent Chunking Engine

**Feature**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13

This document defines every entity introduced or changed by this feature. All new Pydantic
models live in `src/core/chunking/models.py` unless otherwise noted. Changes to existing
models are additive (FR-031/FR-032).

---

## 0. Vocabulary Extension (change to existing entity)

**File**: `src/core/document_intelligence/model.py`

`StructuralElementType` Literal and `CANONICAL_ELEMENT_TYPES` frozenset gain four new values:

| New type | Semantics | Atomic by default? |
|---|---|---|
| `heading` | A titled section heading (h1–h6 equivalent) | Yes — not split; not merged with unrelated text |
| `code-block` | A verbatim code or pre-formatted block | Yes — `code_integrity` enforced (FR-006) |
| `quote` | A block quotation | Yes — `quote_integrity` enforced (FR-006) |
| `figure-placeholder` | A figure reference with optional caption | Yes — own chunk regardless of text content (FR-007) |

Existing six types (`section`, `paragraph`, `table`, `table-row`, `list`, `list-item`) are
unchanged in meaning. The `model_validator` text/fields rule extends naturally — all four new types
use `text` (possibly empty for `figure-placeholder`).

Forward-compat fallback (FR-005): the chunking engine treats any unrecognized type as
`paragraph`-equivalent (same rule as the existing `_DEFAULT_GROUP` fallback in `chunk_mapper.py`).

---

## 1. BoundaryCandidate

A potential boundary point between two adjacent structural elements (or element groups). Created
by the chunking engine for every adjacent pair before routing through the evaluator and policy.

| Field | Type | Notes |
|---|---|---|
| `left_element_id` | `str` | `StructuralElement.id` of the left element |
| `right_element_id` | `str` | `StructuralElement.id` of the right element |
| `left_type` | `str` | Element type of the left element |
| `right_type` | `str` | Element type of the right element |
| `left_parent_id` | `str \| None` | `parent_id` of left element (section/heading context) |
| `right_parent_id` | `str \| None` | `parent_id` of right element |
| `accumulated_char_count` | `int` | Rendered char count of elements accumulated so far on the left side |
| `right_char_count` | `int` | Rendered char count of the right element |

---

## 2. SizeBudgetStatus

```python
SizeBudgetStatus = Literal["within_limit", "over_limit"]
```

---

## 3. BoundaryFeatures

The Semantic Boundary Evaluator's output for one `BoundaryCandidate`. One field per signal
category (FR-044). Never collapsed into a single score.

| Field | Type | Semantics |
|---|---|---|
| `hierarchy_continuity` | `bool` | Left and right share the same structural parent (`parent_id`) |
| `heading_continuity` | `bool` | Right is content under the same heading as left; `False` when right is a new `heading`/`section` |
| `section_continuity` | `bool` | Both elements belong to the same nearest `section`/`heading` ancestor |
| `structural_compatibility` | `bool` | Element types fall in the same compatibility group (prose / tabular / code / figure — see research R8) |
| `lexical_continuity` | `bool` | Text flows naturally between elements; `False` only when types are fundamentally incompatible (rule-based, no NLP) |
| `table_integrity` | `bool` | Merging would not fragment a table across different table parents |
| `list_integrity` | `bool` | Merging would not fragment a list across different list parents |
| `code_integrity` | `bool` | Code block is kept atomic (not merged with non-code elements) |
| `quote_integrity` | `bool` | Quote block is kept atomic (not merged with non-quote elements) |
| `layout_continuity` | `bool` | Elements appear spatially adjacent; `True` for formats without page provenance |
| `size_budget` | `SizeBudgetStatus` | Whether `accumulated + right ≤ max_chars` |

**Validation rules**:
- All fields required; no nullable fields
- Serializable to/from JSON (FR-044 / SC-013)
- Reusable unmodified by any `BoundaryDecisionPolicy` (no mutation)

---

## 4. BoundaryDecision

The output of one `BoundaryDecisionPolicy.decide()` call for one `BoundaryCandidate` (FR-045).
Never contains a probabilistic confidence score or a constructed Chunk.

| Field | Type | Notes |
|---|---|---|
| `decision` | `Literal["merge", "split"]` | The resolved boundary outcome |
| `applied_rule` | `str` | Name of the rule that produced the decision (e.g., `"code_integrity"`, `"size_budget"`, `"default_merge"`) |
| `triggered_features` | `list[str]` | Names of `BoundaryFeatures` fields that drove the decision (non-empty; references valid field names) |
| `rationale` | `str` | Human-readable explanation sufficient for replay (FR-048) |

**Validation rules**:
- `triggered_features` MUST be non-empty and reference only fields present in `BoundaryFeatures`
- No numeric confidence/probability field permitted (FR-045 / SC-016)
- Serializable to/from JSON (SC-013)

---

## 5. ChunkLineage

Traceability record attached to every produced Chunk (FR-013).

| Field | Type | Notes |
|---|---|---|
| `source_element_ids` | `list[str]` | Ordered `StructuralElement.id`s merged into this chunk |
| `applied_rule` | `str` | Rule from the closing `BoundaryDecision` (or `"oversized_element_fallback"`) |
| `triggered_features` | `list[str]` | Features from the closing `BoundaryDecision` |
| `rationale` | `str` | Explanation from the closing `BoundaryDecision` |
| `oversized_split_index` | `int \| None` | Non-null when chunk is a fragment of an oversized element (FR-018) |

---

## 6. StructuralContext

Heading/section path and position metadata attached to every produced Chunk (FR-009).

| Field | Type | Notes |
|---|---|---|
| `element_type` | `str` | Canonical type this chunk primarily represents |
| `heading_path` | `list[str]` | Ordered enclosing heading/section titles (innermost last) |
| `position` | `int` | 0-based document-order position of this chunk in the Chunk Set |

---

## 7. ChunkIdentity

The stable, deterministic identity assigned to a closed Chunk (FR-008/FR-009).

| Field | Type | Notes |
|---|---|---|
| `chunk_id` | `str` | `"ck_" + SHA256("{asset_id}|{sorted_element_ids}|{strategy_id}|{config_hash}")[:16]` |
| `document_id` | `str` | String cast of `DocumentModel.asset_id` |
| `strategy_id` | `str` | Registered strategy name |
| `source_element_ids` | `list[str]` | Sorted source element ids used to derive `chunk_id` |

---

## 8. ChunkRelationships

Parent/child hierarchy and reading-order adjacency links (FR-010/FR-011/FR-012).

| Field | Type | Notes |
|---|---|---|
| `parent_chunk_id` | `str \| None` | Enclosing section-level chunk id; `None` for top-level chunks |
| `previous_chunk_id` | `str \| None` | Reading-order predecessor; `None` for first chunk |
| `next_chunk_id` | `str \| None` | Reading-order successor; `None` for last chunk |
| `child_chunk_ids` | `list[str]` | Finer-grained chunks under this chunk; empty for leaf chunks |

**Validation rules**:
- Every referenced id MUST correspond to an actual chunk in the same `ChunkSet` (FR-012)
- Dangling references are a validation failure (`referential_integrity` quality rule)

---

## 9. Chunk (extended)

The Chunk Builder's output — a retrieval-ready unit (FR-008–FR-014). Extends the existing
`{"text": str, "metadata": dict}` record emitted by `map_elements_to_chunks` with rich
structured fields, while keeping the `text`/`metadata` output contract unchanged (FR-031/FR-032).

| Field | Type | Notes |
|---|---|---|
| `text` | `str` | Rendered chunk text (unchanged from existing contract) |
| `metadata` | `dict[str, Any]` | Backward-compatible metadata dict; new keys are additive |
| `identity` | `ChunkIdentity` | Stable id, strategy, source elements |
| `relationships` | `ChunkRelationships` | Parent/child/prev/next links |
| `lineage` | `ChunkLineage` | Source traceability |
| `structural_context` | `StructuralContext` | Heading path, element type, position |

**New additive `metadata` keys** (in addition to existing keys preserved from `006`):

| Key | Type | Notes |
|---|---|---|
| `chunk_id` | `str` | From `identity.chunk_id` |
| `parent_chunk_id` | `str \| None` | From `relationships.parent_chunk_id` |
| `previous_chunk_id` | `str \| None` | From `relationships.previous_chunk_id` |
| `next_chunk_id` | `str \| None` | From `relationships.next_chunk_id` |
| `heading_path` | `list[str]` | From `structural_context.heading_path` |
| `chunk_position` | `int` | From `structural_context.position` |
| `lineage` | `dict` | Serialized `ChunkLineage` |

---

## 10. ValidationReport

The Chunk Validation stage's structured output — exactly one per chunking run (FR-046).

| Field | Type | Notes |
|---|---|---|
| `status` | `Literal["pass", "fail", "pass_with_warnings"]` | Overall validation outcome |
| `failed_rules` | `list[str]` | `ChunkQualityRule.rule_id` values of failed constraints |
| `warnings` | `list[str]` | `rule_id` values of non-blocking issues |
| `validation_messages` | `list[str]` | Human-readable descriptions (one per failed/warning rule) |

**Named quality rules** (referenced by `failed_rules`/`warnings`):

| rule_id | Type | What it checks |
|---|---|---|
| `min_content` | hard | Chunk text is non-empty and non-whitespace-only (FR-023) |
| `max_size` | hard | Chunk text ≤ `max_chars` (FR-024), except documented oversized-element fragments |
| `no_orphaned_heading` | hard | Heading element is not the sole content of a chunk with no child chunks (FR-019) |
| `no_cross_section_merge` | hard | No chunk's source elements span more than one section (FR-022) |
| `no_mid_row_split` | hard | No table-row element is split (FR-021) |
| `referential_integrity` | hard | Every `parent_chunk_id`, `previous_chunk_id`, `next_chunk_id`, and `child_chunk_ids` entry resolves to an actual chunk in the set (FR-012) |
| `figure_provenance` | warning | `figure-placeholder` chunk has non-null figure provenance metadata (FR-007) |

**Validation rules**:
- `ValidationReport` MUST NOT be a bare boolean — always a structured entity (FR-046)
- Produced before `ChunkSet` is returned; available for replay without re-running the engine (FR-026 / SC-014)

---

## 11. ChunkSet

The pipeline's terminal output — the complete, validated collection of Chunks for one document.

| Field | Type | Notes |
|---|---|---|
| `chunks` | `list[Chunk]` | Ordered by document reading order (chunk_position) |
| `validation_report` | `ValidationReport` | Exactly one per run (FR-046) |
| `asset_id` | `str` | Source document asset id |
| `strategy_id` | `str` | Strategy used to produce this set |
| `element_counts_by_type` | `dict[str, int]` | Counts of source elements by type (for NFR-007 logging) |

---

## 12. Strategy Interfaces

**File**: `src/core/chunking/interfaces.py`

### ChunkingStrategy (ABC)

```python
class ChunkingStrategy(ABC):
    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @abstractmethod
    def chunk(self, document_model: DocumentModel, config: ChunkingStrategyConfig) -> ChunkSet: ...
```

### BoundaryDecisionPolicy (Protocol)

```python
class BoundaryDecisionPolicy(Protocol):
    def decide(
        self,
        candidate: BoundaryCandidate,
        features: BoundaryFeatures,
    ) -> BoundaryDecision: ...
```

### ChunkingStrategyConfig (Pydantic)

| Field | Type | Default | Notes |
|---|---|---|---|
| `strategy` | `str` | `"semantic_structural"` | Registered strategy name |
| `max_chars` | `int` | `800` | Maximum chunk character budget |
| `overlap` | `int` | `0` | Character overlap for oversized splits |
| `policy` | `str` | `"rule_based"` | Registered Boundary Decision Policy name |
| `element_mapping` | `dict[str, ElementChunkConfig]` | `{}` | Per-type overrides (layered from pack YAML) |

---

## 13. Default Implementations

### SemanticStructuralChunkingStrategy

**File**: `src/core/chunking/strategies/semantic_structural.py`

Orchestrates the Boundary Decision Pipeline for a `DocumentModel`:
1. Iterates elements, creating `BoundaryCandidate` for each adjacent pair
2. Calls `SemanticBoundaryEvaluator.evaluate(candidate, context) → BoundaryFeatures`
3. Calls `BoundaryDecisionPolicy.decide(candidate, features) → BoundaryDecision`
4. Forwards decisions to `ChunkBuilder`

### RuleBasedBoundaryDecisionPolicy

**File**: `src/core/chunking/strategies/semantic_structural.py`

Implements rule precedence per research R1 (seven-level deterministic priority order).

### SemanticBoundaryEvaluator

**File**: `src/core/chunking/evaluator.py`

Computes all eleven `BoundaryFeatures` fields from the `BoundaryCandidate` and element context.
No embeddings, no LLM calls, no external I/O.

### ChunkBuilder

**File**: `src/core/chunking/builder.py`

Stateful assembler. Lifecycle per research R9:
`open → append → close → assign_identity → build_relationships → emit`

Identity and relationships are assigned only after a chunk is closed (FR-047).
Post-processing pass assigns `previous_chunk_id`/`next_chunk_id` across the full ordered list.

### ChunkValidator

**File**: `src/core/chunking/validator.py`

Applies all six quality rules and produces exactly one `ValidationReport`. Does not mutate chunks.

---

## Entity Relationship Summary

```
DocumentModel (from 006) ──1:N──> StructuralElement (ordered)
StructuralElement(s) ──N:1──> BoundaryCandidate (adjacent pairs)
BoundaryCandidate ──1:1──> BoundaryFeatures (evaluator output)
BoundaryFeatures ──1:1──> BoundaryDecision (policy output)
BoundaryDecision(s) ──N:1──> Chunk (builder output, via lifecycle)
Chunk(s) ──N:1──> ChunkSet (builder final output)
ChunkSet ──1:1──> ValidationReport (validator output)
Chunk ──has──> ChunkIdentity + ChunkRelationships + ChunkLineage + StructuralContext
Chunk.relationships ──ref──> other Chunk.identity.chunk_id (within same ChunkSet)
ChunkSet ──feeds──> existing DataChunk.chunk_metadata (additive keys; no schema change)
ChunkingStrategy ──selected via──> ChunkingProfile.strategy (pack YAML)
BoundaryDecisionPolicy ──selected via──> ChunkingStrategyConfig.policy
```
