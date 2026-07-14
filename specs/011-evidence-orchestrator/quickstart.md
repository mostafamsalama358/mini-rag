# Quickstart Validation Guide: Evidence Orchestrator (011)

This guide describes how to validate that the Evidence Orchestrator works correctly
end-to-end after implementation. All scenarios use synthetic fixtures — no live LLM,
vector DB, or external API calls are required unless stated.

---

## Prerequisites

- Python 3.13 environment with project dependencies installed:
  ```
  pip install -r requirements.txt
  pip install pytest pytest-asyncio pytest-benchmark
  ```
- Working directory: repo root (`d:/mini-rag` or equivalent)
- No running services required for unit/integration tests (all external dependencies mocked)

---

## Scenario 1 — Smoke Test: Full Pipeline on Minimal Input

**Validates**: FR-007, FR-009, SC-003 (schema completeness)

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_pipeline.py::test_smoke_single_candidate -v
```

### What it does

Constructs a `RetrievalResult` with one `RetrievedCandidate` and a matching
`RetrievalPlan` with no entities. Runs `EvidenceOrchestrator.orchestrate()` with the
default config. Asserts:
- Returns an `EvidencePack` (not an exception)
- `pack.is_empty == False`
- `pack.items` has exactly one `EvidenceItem`
- All mandatory fields on `EvidenceItem` and `Citation` are non-null and correctly typed
- `pack.schema_version == "1.0.0"`

---

## Scenario 2 — Exact-Match Deduplication

**Validates**: FR-002, SC-001, SC-005 (source attribution accuracy)

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_deduplicator.py::test_exact_duplicate_merge -v
```

### What it does

Constructs a `RetrievalResult` with two `RetrievedCandidate` objects sharing the same
`chunk_id` but from different strategies ("semantic" and "keyword") with scores 0.9 and
0.7. Runs deduplication. Asserts:
- Output has exactly one item
- The surviving item's score is 0.9 (higher preserved)
- `sources` list contains both strategy entries

---

## Scenario 3 — Near-Duplicate Deduplication (Embedding Path)

**Validates**: FR-003

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_deduplicator.py::test_near_duplicate_cosine -v
```

### What it does

Provides two candidates with different `chunk_id` but identical `content_excerpt` text
(cosine similarity = 1.0). Uses a mock embedding provider that returns the same vector
for both. Asserts deduplication merges them into one item.

---

## Scenario 4 — Character N-gram Fallback (Large Batch)

**Validates**: FR-003 (fallback path), research D2

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_deduplicator.py::test_character_ngram_fallback -v
```

### What it does

Creates 201 candidates (above default `near_dedup_batch_limit=200`). Verifies that the
deduplicator uses the character n-gram path (logged as `method_used="character_ngram"`)
and still correctly merges known near-duplicates.

---

## Scenario 5 — Expansion Gate: High-Score Chunk Gets Context

**Validates**: FR-004, User Story 3

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_expander.py::test_expansion_high_score -v
```

### What it does

Provides a high-score candidate (score=0.90 ≥ threshold 0.80) with `previous_chunk_id`
set. Mock `IChunkReader` returns a prev-chunk with text "PREV_TEXT". Asserts:
- `EvidenceItem.text` starts with "PREV_TEXT"
- `EvidenceItem.expanded == True`

---

## Scenario 6 — Expansion Disabled

**Validates**: FR-004 (disabled path)

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_expander.py::test_expansion_disabled -v
```

### What it does

Sets `config.expansion_enabled = False`. Provides a high-score candidate with lineage
links. Asserts that `IChunkReader.get_chunk` is never called and the item's text is
unchanged.

---

## Scenario 7 — Compressibility Scoring

**Validates**: FR-005, User Story 4

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_redundancy_scorer.py -v
```

### What it does

Provides three items: one unique high-relevance item, one item whose text is 90%
identical to the first (below dedup threshold), and one low-relevance unique item.
Asserts:
- Unique high-relevance item: `compressibility_score < 0.3`
- Near-duplicate survivor: `compressibility_score > 0.7`
- Low-relevance unique: `compressibility_score` reflects relevance-inverse component

---

## Scenario 8 — Relevance Fusion Prioritization

**Validates**: FR-006, User Story 2

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_fusion_prioritizer.py::test_entity_boost -v
```

### What it does

Provides two items with equal retrieval scores (0.5 each). Item A's text contains 2 of
2 resolved entities from the plan; Item B's text contains 0. Default weights (ret=0.6,
ent=0.3, rec=0.1). Asserts:
- Item A's `relevance_score` > Item B's `relevance_score`
- Items returned in descending order (A first)

---

## Scenario 9 — Empty Input Handling

**Validates**: FR-009, User Story 5 acceptance scenario 3

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_pipeline.py::test_empty_candidates -v
```

### What it does

Passes a `RetrievalResult` with `candidates=()`. Asserts:
- `EvidencePack.is_empty == True`
- `EvidencePack.items == []`
- `EvidencePack.raw_candidate_count == 0`
- No exception raised

---

## Scenario 10 — Token Reduction Ratio (SC-002 Validation)

**Validates**: FR-013, SC-002

### Run

```
pytest tests/unit/core/evidence_orchestrator/test_pack_assembler.py::test_token_reduction_ratio -v
```

### What it does

Creates 10 raw candidates with identical text (deliberate duplicates). After dedup, pack
has 1 item. Asserts:
- `token_reduction_ratio ≤ 0.85` (at least 15% reduction)
- `token_reduction_ratio > 0.0`

---

## Scenario 11 — End-to-End Integration

**Validates**: All FRs, SC-001 through SC-006

### Run

```
pytest tests/integration/test_evidence_orchestrator_e2e.py -v
```

### What it does

Uses the full `EvidenceOrchestrator` pipeline with:
- A `RetrievalResult` containing 20 candidates: 8 exact duplicates across two strategies,
  4 near-duplicates (cosine similarity 0.97), and 8 unique items.
- A `RetrievalPlan` with 3 resolved entities, 2 of which appear in the top items.
- Mock embedding provider (deterministic vectors).
- Mock `IChunkReader` (returns canned adjacent chunks for 2 high-score items).
- Character approximation token counter.

Asserts the final `EvidencePack`:
- `items` has ≤ 12 items (20 - 8 exact - 4 near = 8 unique, plus merge survivors)
- Item count reduction ≥ 20% from 20 raw candidates (SC-001)
- `token_reduction_ratio ≤ 0.85` (SC-002)
- All `EvidenceItem` fields non-null and schema-valid (SC-003)
- `items` sorted descending by `relevance_score`
- Items that had entity matches rank above equal-score items without (SC-005)
- `EvidencePack.schema_version == "1.0.0"`

---

## Scenario 12 — Latency Benchmark (SC-004 Baseline)

**Validates**: SC-004 (baseline measurement; not a hard gate)

### Run

```
pytest tests/integration/test_evidence_orchestrator_e2e.py::test_pipeline_latency_benchmark --benchmark-only -v
```

### What it does

Runs the full orchestration pipeline on a synthetic 100-candidate input (50% exact
duplicates, mock embeddings, mock chunk reader) 20 times. Reports p50 and p95 latency.
The p50 result becomes the official SC-004 baseline for this feature. The test does NOT
fail if latency exceeds 500 ms — it only records the measurement.

### Expected output

```
Benchmark results:
  orchestrate/100-candidates   p50=XXX ms   p95=XXX ms
```

Record `p50` in `specs/011-evidence-orchestrator/plan.md` after the first run.

---

## Configuration Reference

The generic field-pack config at `src/fields/generic/evidence_orchestrator.yaml`
controls all thresholds. See `data-model.md` → `EvidenceOrchestratorConfig` for
the full schema. Domain packs (pharmacy, legal) may override any key.

See [contracts/](contracts/) for full interface specifications.
See [data-model.md](data-model.md) for the `EvidencePack` and `EvidenceItem` schemas.
