# Quickstart: Retrieval Planner Validation

**Feature**: `009-retrieval-planner` | **Date**: 2026-07-14

This guide covers how to validate that the Retrieval Planner implementation is correct
end-to-end. It does **not** contain implementation code — see `data-model.md` for model
definitions and `contracts/pipeline-contract.md` for the stable contract.

---

## Prerequisites

- Python 3.13 environment activated
- Dependencies installed: `pip install -r requirements.txt`
- Working directory: repo root (`d:/mini-rag`)
- No external services required — the Planner is a stateless, in-memory component

---

## Validation Scenario 1 — Unambiguous Factual Query (SC-001, SC-003, SC-006)

**Goal**: Verify that a clear query produces a fully populated `RetrievalPlan` with
`clarification_required=False`, a non-empty ordered `retrieval_strategies` list, and
no retrieval execution.

**Setup**: Use the generic field pack (`src/fields/generic/retrieval_planning.yaml`).
Construct a `ParseResult` with:
- `canonical_query = "What are the contraindications for ibuprofen?"`
- `query_plan.operation = "lookup"`
- `query_plan.entities = ["ibuprofen"]`
- `query_plan.language = "en"`
- `query_plan.confidence = 0.95`
- `query_plan.needs_clarification = False`

**Run**: `pytest tests/unit/core/retrieval_planner/test_plan_assembler.py -k factual`

**Expected plan shape**:
- `intent.category` = `"factual"`
- `intent.confidence` >= `0.8`
- `entities[0].canonical_form` = `"ibuprofen"`
- `retrieval_strategies` includes `"semantic"` as first entry
- `retrieval_strategies` is non-empty
- `retrieval_limits.scope` = `"narrow"`
- `retrieval_limits.max_evidence_units` = `5`
- `retrieval_constraints.citation_required` = `True`
- `retrieval_constraints.required_language` = `"en"`
- `clarification_required` = `False`
- `clarification_question` = `None`
- `planner_confidence` >= `0.8`
- `diagnostics` = `None` (production config)

**Determinism check**: Call `plan()` twice with the same input. Assert
`plan_a.metadata.plan_id == plan_b.metadata.plan_id`.

---

## Validation Scenario 2 — Ambiguous Query Triggers Clarification (SC-005)

**Goal**: Verify that an under-specified query sets `clarification_required=True` and
returns a question without producing a retrieval plan body.

**Setup**: Construct a `ParseResult` with:
- `canonical_query = "Tell me about it"`
- `query_plan.operation = "unsupported"`
- `query_plan.entities = []`
- `query_plan.confidence = 0.2`
- `query_plan.needs_clarification = False`

**Run**: `pytest tests/unit/core/retrieval_planner/test_clarification_detector.py`

**Expected plan shape**:
- `clarification_required` = `True`
- `clarification_question` is non-empty (`len > 0`)
- `retrieval_strategies` is empty (`len == 0`)
- `planner_confidence` <= `0.5`

---

## Validation Scenario 3 — Tabular Query Selects Table Strategy (SC-004)

**Goal**: Verify that a table-oriented query produces `table` in `retrieval_strategies`.

**Setup**: Construct a `ParseResult` with:
- `canonical_query = "Show me the dosage table for aspirin"`
- `query_plan.operation = "lookup"`
- `query_plan.entities = ["aspirin"]`
- `query_plan.confidence = 0.9`
- `query_plan.needs_clarification = False`

**Run**: `pytest tests/unit/core/retrieval_planner/test_strategy_selector.py -k tabular`

**Expected**:
- `intent.category` = `"tabular"`
- `"table"` is in `retrieval_strategies`
- `retrieval_limits.max_evidence_units` = `3`

---

## Validation Scenario 4 — Domain Field Pack Switch (SC-008)

**Goal**: Verify that the same query with two different field packs produces different
strategy and budget outputs without any code changes.

**Setup**:
- Run Scenario 1 query with `generic` field pack → record `retrieval_strategies`, `retrieval_limits`
- Create or load a field pack that excludes `"semantic"` from `available_strategies`
  and sets a lower `max_evidence_units` ceiling
- Run the same query with this restricted field pack

**Run**: `pytest tests/unit/core/retrieval_planner/test_strategy_selector.py -k domain_pack`

**Expected**:
- With restricted pack: `"semantic"` does NOT appear in `retrieval_strategies`
- `retrieval_limits.max_evidence_units` reflects the pack ceiling, not the default

---

## Validation Scenario 5 — Zero Retrieval Operations (SC-006)

**Goal**: Verify statically that the planner core imports no retrieval infrastructure.

**Run**:
```
pytest tests/unit/core/retrieval_planner/test_models.py -k no_retrieval_imports
```

This test uses Python's `importlib` / `ast` to inspect `src/core/retrieval_planner/`
for any import of retrieval-engine modules (`core.retrieval`, `stores.vectordb`,
`stores.llm`, PostgreSQL drivers, BM25 libraries, etc.) and asserts zero matches.

---

## Validation Scenario 6 — New StrategyType via YAML (SC-010)

**Goal**: Verify that a new strategy type added to a field pack YAML is selectable by
the Planner with zero code changes.

**Setup**:
- Add `"citations_graph"` to `available_strategies` in a custom field pack YAML
- Add a mapping `factual: ["citations_graph", "semantic"]` to `strategy_mappings`
- Run the factual query from Scenario 1 with this custom pack

**Expected**:
- `retrieval_strategies[0]` = `"citations_graph"`
- No exception raised; no Planner source file modified

---

## Validation Scenario 7 — Contract Stability (SC-007, SC-011)

**Goal**: Verify that the `RetrievalPlan` schema version is present and parseable.

**Run**: `pytest tests/unit/core/retrieval_planner/test_models.py -k schema_version`

**Expected**:
- Every `RetrievalPlan` instance has `metadata.schema_version = "1.0.0"`
- `schema_version` follows semantic versioning format (`MAJOR.MINOR.PATCH`)
- `metadata.plan_id` starts with `"rp_"` and has exactly 19 characters

---

## Golden Plan Suite (SC-004, SC-005)

The golden plan suite in `tests/integration/test_retrieval_planner_golden.py` validates
15+ labelled query fixtures against expected plan shapes. Run it with:

```
pytest tests/integration/test_retrieval_planner_golden.py -v
```

Each golden test asserts:
- `intent.category` matches the labelled expected category
- Primary strategy matches the labelled expected strategy
- `clarification_required` matches the labelled ambiguity flag
- Plan is reproducible (two runs, same `plan_id`)

Pass criteria (SC-004): ≥ 90% of golden queries assigned the expected primary strategy.
Pass criteria (SC-005): ≥ 85% precision on labelled ambiguous queries
(no excessive false positives blocking clear queries).

---

## Latency Validation (SC-002)

To verify the 50 ms planning latency target:

```
pytest tests/integration/test_retrieval_planner_golden.py -v --benchmark
```

The benchmark flag runs each golden fixture 100 times and asserts p95 planning latency
≤ 50 ms (pipeline only, excluding test harness overhead). This test is skipped in CI
by default and run explicitly for performance validation.

---

## References

- Data model: [data-model.md](data-model.md)
- Public contract: [contracts/pipeline-contract.md](contracts/pipeline-contract.md)
- Spec: [spec.md](spec.md)
- Field pack (generic): `src/fields/generic/retrieval_planning.yaml`
- Unit tests: `tests/unit/core/retrieval_planner/`
- Integration tests: `tests/integration/test_retrieval_planner_golden.py`
