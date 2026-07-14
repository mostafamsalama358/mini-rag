# Quickstart: Context Builder Validation Guide (spec 012)

**Date**: 2026-07-14
**Purpose**: Prove the feature works end-to-end without a live LLM or database.

---

## Prerequisites

- Python 3.13 installed
- Repo cloned; working directory: `d:/mini-rag/src` (or `src/` from repo root)
- `pip install -r requirements.txt` completed
- spec 011 (`evidence_orchestrator`) tests passing (Context Builder imports from it)

---

## Scenario 1 — Budget-Compliant Assembly

**What this proves**: Given an `EvidencePack` exceeding the token budget, the pipeline
outputs a `Context` within budget, retaining highest-ranked items and preserving all
citations.

### Setup

```python
# conftest fixture or inline in test
from core.evidence_orchestrator.models import (
    EvidencePack, EvidenceItem, Citation, EvidenceItemSource
)
from core.context_builder.config import ContextBuilderConfig, BudgetReservations
from core.context_builder.pipeline import ContextBuilderPipeline
from core.context_builder.registry import ContextBuilderRegistry

# 20 items × ~600 tokens each = ~12 000 tokens total
# Budget: 8000 window − 500 system − 200 question − 1000 output = 6300 available
config = ContextBuilderConfig(
    total_context_window=8000,
    reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
    compression_enabled=True,
    compressibility_threshold=0.7,
    final_dedup_enabled=True,
)
pack = build_synthetic_pack(n_items=20, tokens_per_item=600)  # helper in conftest
pipeline = ContextBuilderRegistry.build(config)
```

### Run

```python
import asyncio
ctx = asyncio.run(pipeline.build(pack, config))
```

### Expected Outcomes

```
assert ctx.token_count <= 6300
assert len(ctx.ordered_blocks) < 20          # some items dropped
assert len(ctx.ordered_blocks) == len(ctx.citation_map)   # zero broken citations
assert ctx.metadata.items_dropped > 0
assert ctx.metadata.budget_used == ctx.token_count
```

---

## Scenario 2 — High-Compressibility Items Compressed First

**What this proves**: Items with `compressibility_score > 0.7` are compressed before
lower-scored items are dropped; graceful degradation ordering is measurable.

### Setup

```python
# 5 high-compressibility items (score=0.9) + 5 low-compressibility (score=0.1)
# Budget only fits ~4 items uncompressed
pack = build_pack_with_mix(
    high_compress_count=5, high_score=0.9,
    low_compress_count=5,  low_score=0.1,
    tokens_per_item=1200,
)
config = ContextBuilderConfig(total_context_window=4000, ...)
ctx = asyncio.run(pipeline.build(pack, config))
```

### Expected Outcomes

```
# Low-compressibility items are retained; high-compressibility are compressed/dropped
low_ids  = {i.item_id for i in pack.items if i.compressibility_score < 0.5}
high_ids = {i.item_id for i in pack.items if i.compressibility_score > 0.7}
included = {b.item_id for b in ctx.ordered_blocks}

assert low_ids.issubset(included)        # all low-compress items survived
assert ctx.metadata.items_compressed > 0  # compression was applied to high-compress
```

---

## Scenario 3 — Conflict Detection

**What this proves**: Two items referencing the same entity with different numeric
values produce a `ConflictGroup` in `Context.conflicts`.

### Setup

```python
item_a = make_item(
    entity_tags=["metformin"],
    text="Patients received metformin 500mg twice daily.",
)
item_b = make_item(
    entity_tags=["metformin"],
    text="The dosage of metformin was 1000mg per day.",
)
pack = make_pack([item_a, item_b])
ctx = asyncio.run(pipeline.build(pack, config))
```

### Expected Outcomes

```
assert len(ctx.conflicts) == 1
cg = ctx.conflicts[0]
assert cg.entity_tag == "metformin"
assert set(cg.item_ids) == {item_a.item_id, item_b.item_id}
assert cg.resolution is None   # both items survived (budget not a factor here)
```

---

## Scenario 4 — Document-Structure Ordering

**What this proves**: Items from two documents are grouped by document, ordered by
`section_path` depth, not by relevance score.

### Setup

```python
items = [
    make_item(doc_id="docA", section_path=["Results"], relevance_score=0.5),
    make_item(doc_id="docA", section_path=["Introduction"], relevance_score=0.9),
    make_item(doc_id="docB", section_path=["Summary"], relevance_score=0.7),
]
pack = make_pack(items)
ctx = asyncio.run(pipeline.build(pack, config))
```

### Expected Outcomes

```
blocks = ctx.ordered_blocks
doc_ids = [b.document_id for b in blocks]

# All docA blocks come before docB blocks
assert doc_ids.index("docA") < doc_ids.index("docB")

# Within docA: Introduction before Results (alphabetical section_path order)
docA_blocks = [b for b in blocks if b.document_id == "docA"]
assert docA_blocks[0].section_path == "Introduction"
assert docA_blocks[1].section_path == "Results"
```

---

## Scenario 5 — Zero Broken Citations

**What this proves**: Every block in any `Context` has a citation; no orphan blocks.

### Run against all four scenarios above

```python
for ctx in [ctx1, ctx2, ctx3, ctx4]:
    block_ids = {b.item_id for b in ctx.ordered_blocks}
    citation_ids = set(ctx.citation_map.keys())
    assert block_ids == citation_ids, f"Citation mismatch: {block_ids ^ citation_ids}"
```

---

## Scenario 6 — Empty Pack Handled Gracefully

**What this proves**: An empty `EvidencePack` produces an empty `Context` with no error.

```python
empty_pack = make_empty_pack()
ctx = asyncio.run(pipeline.build(empty_pack, config))

assert ctx.token_count == 0
assert ctx.ordered_blocks == []
assert ctx.citation_map == {}
assert ctx.conflicts == []
assert ctx.metadata.items_included == 0
```

---

## Running Unit Tests

```bash
# from repo root
pytest tests/unit/core/context_builder/ -v
```

Expected: all stages pass independently with mock inputs.

## Running Integration Test

```bash
pytest tests/integration/test_context_builder_e2e.py -v
```

Expected: end-to-end pipeline (with real `EvidencePack` fixture and heuristic
compressor) completes and satisfies all contract invariants from
[contracts/Context.md](contracts/Context.md).

## Performance Check

```bash
pytest tests/unit/core/context_builder/test_pipeline.py -v -k "bench"
```

Expected: median assembly time on 50-item pack ≤ 150 ms (SC-005), measured with
`time.perf_counter` in the test fixture (no live LLM; heuristic compressor only).

---

## Key Reference Links

- [Context output schema](contracts/Context.md)
- [ITokenBudgetAllocator contract](contracts/ITokenBudgetAllocator.md)
- [IContextCompressor contract](contracts/IContextCompressor.md)
- [IConflictDetector contract](contracts/IConflictDetector.md)
- [IContextStitcher contract](contracts/IContextStitcher.md)
- [Data model](data-model.md)
- [Research decisions](research.md)
- [Upstream EvidencePack contract](../011-evidence-orchestrator/contracts/EvidencePack.md)

---

## Validation Results (2026-07-14)

Manual quickstart validation via `pytest tests/integration/test_context_builder_e2e.py`:

| Scenario | Result |
|----------|--------|
| 1 — Budget compliance | PASS — `ctx.token_count <= 6300`, citations 1:1 |
| 2 — Compressibility ordering | PASS — low-compressibility items retained |
| 3 — Conflict detection | PASS — metformin dosage conflict detected |
| 4 — Document ordering | PASS — docA before docB, Introduction before Results |
| 5 — Zero broken citations | PASS — block_ids == citation_ids across scenarios |
| 6 — Empty pack | PASS — empty Context, no exception |

Performance: `pytest tests/unit/core/context_builder/test_pipeline.py -k bench` — median ≤ 150 ms on 50-item pack.
