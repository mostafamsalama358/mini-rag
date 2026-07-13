# Quickstart & Validation Guide: Intelligent Chunking Engine

**Feature**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13

This guide documents the runnable validation scenarios that prove the feature works
end-to-end. All scenarios use pytest fixture files located in `tests/fixtures/chunking/`.
No live LLM/embedding calls are needed — the engine is fully deterministic and CPU-only.

---

## Prerequisites

```bash
# Start from the repo root with Docker Compose services running
docker compose up -d postgres rabbitmq

# Install dependencies (if not already in your dev environment)
pip install -r src/requirements.txt

# Verify existing tests still pass (regression gate)
cd src && pytest tests/unit/ tests/integration/ -q --tb=short
```

---

## Scenario 1 — Semantic Boundary Decisions over Token Utilization (SC-001, SC-002, US-1)

**Validates**: Headings stay with content; table rows are never split mid-row; unrelated
sections are never merged.

**Fixture**: `tests/fixtures/chunking/heading_table_sections.py`

```python
# Fixture DocumentModel: heading → 3 paragraphs → table (4 rows) → new section → paragraph
from core.document_intelligence.model import DocumentModel, StructuralElement

FIXTURE_DOC = DocumentModel(
    asset_id="test-001",
    source_format="txt",
    elements=[
        StructuralElement(id="test-001:h1", type="heading", order=0, text="Section A"),
        StructuralElement(id="test-001:p1", type="paragraph", order=1, text="Paragraph one."),
        StructuralElement(id="test-001:p2", type="paragraph", order=2, text="Paragraph two."),
        StructuralElement(id="test-001:t1", type="table", order=3, text="Table header."),
        StructuralElement(id="test-001:tr1", type="table-row", order=4,
                          fields={"col1": "A", "col2": "B"}, parent_id="test-001:t1"),
        StructuralElement(id="test-001:tr2", type="table-row", order=5,
                          fields={"col1": "C", "col2": "D"}, parent_id="test-001:t1"),
        StructuralElement(id="test-001:h2", type="heading", order=6, text="Section B"),
        StructuralElement(id="test-001:p3", type="paragraph", order=7, text="Separate section."),
    ],
)
```

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_semantic_boundaries.py -v
```

**Expected outcomes**:
- No chunk separates `test-001:h1` from `test-001:p1` (heading_continuity enforced)
- `test-001:tr1` and `test-001:tr2` are in separate chunks (table-row non-grouping default)
- No chunk contains elements from both Section A and Section B (`section_continuity` enforced)
- `test-001:h1` appears in `heading_path` of all chunks produced under Section A

---

## Scenario 2 — Strategy Swappability (SC-004, SC-010, US-2)

**Validates**: Switching the active strategy requires zero code changes outside the strategy
module and its registration; indexing/retrieval/storage code paths are unaffected.

**Steps**:

```bash
# 1. Run integration test with the default strategy
cd src && pytest tests/integration/chunking/test_strategy_swap.py::test_default_strategy -v

# 2. The test registers a no-op 'passthrough' strategy that emits one chunk per element
#    and switches a test project's config to use it.
#    Verify the test output shows the strategy changed but the metadata shape is identical.
cd src && pytest tests/integration/chunking/test_strategy_swap.py::test_passthrough_strategy -v

# 3. Confirm zero diffs under indexing, retrieval, and storage code (SC-004)
cd src && pytest tests/integration/chunking/test_strategy_swap.py::test_downstream_contract_unchanged -v
```

**Expected outcomes**:
- Both strategies produce `{"text": ..., "metadata": {...}}` records with identical key sets
- `chunk_metadata.element_type`, `source_element_ids`, `file_name` populated in both cases
- No change to `tasks/data_indexing.py`, `services/rag/`, or DB schema required

---

## Scenario 3 — Hierarchical, Relationship-Aware Output (SC-005, US-3)

**Validates**: Parent/child and previous/next links are referentially valid and reconstruct
document order.

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_relationships.py -v
```

**Expected outcomes**:
- Every `child_chunk_id` in a section chunk corresponds to an actual chunk in the set
- Following `next_chunk_id` from `chunk_position=0` visits every chunk exactly once in order
- No dangling `parent_chunk_id`, `previous_chunk_id`, or `next_chunk_id` references
- `referential_integrity` rule in `ValidationReport.failed_rules` is empty

---

## Scenario 4 — Stable Identity & Determinism (SC-003, SC-009, SC-015, US-4)

**Validates**: Two runs of the same fixture produce identical output; BoundaryFeatures and
BoundaryDecision are deterministic and independently reproducible.

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_determinism.py -v
```

**What the test does**:
1. Chunks `FIXTURE_DOC` (Scenario 1) with the default strategy twice
2. Asserts all `chunk_id`, `text`, `heading_path`, `lineage`, and relationship fields are identical
3. Replays each `BoundaryDecision` through the same policy with the same `BoundaryFeatures`
   and asserts the reproduced decision is identical (SC-015)
4. Asserts no `BoundaryDecision` contains a numeric confidence/probability field (SC-016)

---

## Scenario 5 — Extended Structural Types (SC-006, US-5)

**Validates**: `code-block`, `quote`, and `figure-placeholder` are treated as atomic,
addressable units.

**Fixture**: `tests/fixtures/chunking/extended_types.py`

```python
EXTENDED_DOC = DocumentModel(
    asset_id="test-002",
    source_format="txt",
    elements=[
        StructuralElement(id="test-002:p1", type="paragraph", order=0, text="Before code."),
        StructuralElement(id="test-002:cb1", type="code-block", order=1,
                          text="def foo():\n    return 42"),
        StructuralElement(id="test-002:p2", type="paragraph", order=2, text="After code."),
        StructuralElement(id="test-002:q1", type="quote", order=3,
                          text="The only way to do great work is to love what you do."),
        StructuralElement(id="test-002:fig1", type="figure-placeholder", order=4,
                          text="[Figure 1: Architecture diagram]"),
    ],
)
```

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_extended_types.py -v
```

**Expected outcomes**:
- `test-002:cb1` is NOT merged with `test-002:p1` or `test-002:p2` (`code_integrity` enforced)
- `test-002:fig1` produces its own chunk even though it has minimal text (FR-007)
- `test-002:q1` is its own chunk (`quote_integrity` enforced)
- All three produce non-empty chunks with `chunk_id` set

---

## Scenario 6 — Validation Gate (SC-007, SC-014, US-6)

**Validates**: The validation gate catches all quality violations; ValidationReport is a
faithful structured report (not a bare boolean).

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_validation.py -v
```

**What the test does**:
1. Directly invokes `ChunkValidator` on fixture chunk sets containing injected violations:
   - Empty/whitespace-only chunk → `min_content` in `failed_rules`
   - Chunk exceeding `max_chars` → `max_size` in `failed_rules`
   - Orphaned heading chunk (no children, no following content) → `no_orphaned_heading`
   - Chunk spanning two sections → `no_cross_section_merge`
   - Split table-row → `no_mid_row_split`
   - Dangling `parent_chunk_id` → `referential_integrity`
2. Asserts each violation appears in `ValidationReport.failed_rules` or `warnings`
3. Asserts `ValidationReport.validation_messages` is non-empty and human-readable
4. Re-runs validation on the same chunks and asserts identical report (SC-014)

---

## Scenario 7 — BoundaryFeatures Serialization (SC-013)

**Validates**: `BoundaryFeatures` and `BoundaryDecision` round-trip through JSON without loss.

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_serialization.py -v
```

**Expected outcomes**:
- `BoundaryFeatures.model_dump()` → `json.dumps()` → `json.loads()` → `BoundaryFeatures.model_validate()` produces equal instances
- Same round-trip for `BoundaryDecision`
- No field is lost or type-coerced

---

## Scenario 8 — Performance Baseline (SC-008)

**Validates**: End-to-end chunking time does not regress by more than 2× vs the current
heuristic baseline.

```bash
# Record baseline (run once; commits result to tests/integration/benchmarks/)
cd src && pytest tests/integration/benchmarks/test_chunking_benchmark.py \
    --benchmark-save=baseline --benchmark-only -v

# After implementation, compare:
cd src && pytest tests/integration/benchmarks/test_chunking_benchmark.py \
    --benchmark-compare=baseline -v
```

**Pass criterion**: New engine median ≤ 2× baseline median per document (research R5).

---

## Scenario 9 — Chunk Builder Lifecycle Integrity (SC-012, SC-016)

**Validates**: No chunk is assigned identity/relationships before closing; no BoundaryDecision
or ValidationReport contains a confidence/probability field.

**Run**:

```bash
cd src && pytest tests/unit/chunking/test_builder_lifecycle.py -v
```

**What the test does**:
1. Instruments `ChunkBuilder` to record when `identity` and `relationships` are first assigned
2. Asserts they are always assigned **after** the chunk is closed, never before (FR-047)
3. Asserts all produced `BoundaryDecision` instances have no numeric field (SC-016)
4. Asserts `ValidationReport` status is always one of `"pass"`, `"fail"`, `"pass_with_warnings"`

---

## Reference

- Data model: `specs/007-intelligent-chunking-engine/data-model.md`
- Strategy contract: `specs/007-intelligent-chunking-engine/contracts/chunking-strategy-contract.md`
- Policy contract: `specs/007-intelligent-chunking-engine/contracts/boundary-decision-policy-contract.md`
- Output contract: `specs/007-intelligent-chunking-engine/contracts/chunk-output-contract.md`
- Research decisions: `specs/007-intelligent-chunking-engine/research.md`
