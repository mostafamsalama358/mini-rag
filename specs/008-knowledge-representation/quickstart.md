# Quickstart Validation Guide: Knowledge Representation

**Feature**: `008-knowledge-representation` | **Date**: 2026-07-13

This guide documents runnable validation scenarios that prove the Knowledge Representation
stage works end-to-end. Each scenario maps to one or more Success Criteria (SC-*) from the
spec. All scenarios run against fixture ChunkSets defined in `tests/unit/core/knowledge/conftest.py`.

---

## Prerequisites

**Software**:
- Python 3.13
- Docker + Docker Compose (for integration tests that need PostgreSQL)

**Install**:
```bash
pip install -r src/requirements.txt
pip install pytest pytest-asyncio
```

**Start services** (integration tests only):
```bash
docker compose up -d postgres
```

---

## Fixture ChunkSet Structure

The `conftest.py` provides the following reusable fixtures:

| Fixture | Contents | Used by |
|---------|----------|---------|
| `chunk_set_five_forms` | 5 chunks: procedure (numbered steps), definition (`"X is defined as"`), measurement (`"5 mg per dose"`), table-row element, plain assertion | SC-001, SC-002, SC-007, US-1 |
| `chunk_set_alias_pair` | 2 chunks with same concept under two surface forms (e.g., "ASA" and "acetylsalicylic acid") | SC-010, US-4 |
| `chunk_set_single_degraded` | 1 chunk (fallback/degraded, empty text) | Edge case |
| `chunk_set_malformed` | 3 chunks used to inject intentional violations via post-processing | SC-005, US-6 |
| `chunk_set_ner_compatible` | Chunks containing entity-like proper nouns and numeric values | SC-009 |
| `chunk_set_50_chunks` | 50 mixed-type chunks for latency benchmarking | SC-008 |

---

## Scenario 1 — Five Semantic Forms → Correct KU Types (SC-001, US-1)

**Verify**: A ChunkSet containing five distinct semantic forms produces Knowledge Units
of the correct types, with no chunks silently dropped.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_structural_extractor.py::test_five_forms_correct_types -v
```

**Expected outcomes**:
- `KnowledgeUnit` with `type == "procedure"` extracted from the numbered-steps chunk.
- `KnowledgeUnit` with `type == "definition"` extracted from the definition chunk.
- `KnowledgeUnit` with `type == "measurement"` extracted from the measurement chunk.
- `KnowledgeUnit` with `type == "table"` extracted from the table-row chunk.
- `KnowledgeUnit` with `type == "assertion"` or `"fact"` extracted from the plain prose chunk.
- Total output count == 5 (no chunks dropped).

---

## Scenario 2 — Full Evidence Traceability (SC-002, US-3)

**Verify**: Every Knowledge Unit in a produced package has a non-empty
`evidence_references` collection where every reference resolves through all four
traceability levels.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_models.py::test_evidence_traceability_all_levels -v
```

**Expected outcomes**:
- For every `KnowledgeUnit` in the package: `len(ku.evidence_references) >= 1`.
- For every `EvidenceReference` in every KU: `len(er.chunk_ids) >= 1`,
  `len(er.element_ids) >= 1`, `er.document_model_id` is non-empty,
  `er.asset_id` is non-empty.
- All `er.chunk_ids` entries are present in `chunk_set_five_forms.chunks[*].identity.chunk_id`.
- All `er.element_ids` entries are present in the fixture DocumentModel's element list.
- For every `KnowledgeRelationship`: same traceability check on its `evidence_references`.

---

## Scenario 3 — Idempotent Re-processing (SC-003)

**Verify**: Running the pipeline twice on the same ChunkSet with the same config
produces identical KnowledgePackage contents.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_assembler.py::test_idempotent_reprocessing -v
```

**Expected outcomes**:
- `package1.metadata.package_id == package2.metadata.package_id`
- `[ku.id for ku in package1.knowledge_units] == [ku.id for ku in package2.knowledge_units]`
- `[kr.id for kr in package1.knowledge_relationships] == [kr.id for kr in package2.knowledge_relationships]`
- Every evidence reference id appears identically in both packages.

---

## Scenario 4 — Strategy Swap Without Core Change (SC-004, US-2)

**Verify**: Registering a second extractor and switching configuration to it requires
zero changes to core pipeline code or downstream consumers.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_structural_extractor.py::test_strategy_swap_zero_core_change -v
```

**Setup**: Register a `StubAlternativeExtractor` that produces `assertion`-typed KUs for
all chunks. Switch `config.extractor_strategy` to `"stub_alternative"`.

**Expected outcomes**:
- The pipeline dispatches to `StubAlternativeExtractor` without any `if/else` in core.
- The resulting `KnowledgePackage` has the same structural shape:
  - `knowledge_units`: non-empty tuple of `KnowledgeUnit`
  - `knowledge_relationships`: tuple of `KnowledgeRelationship`
  - `validation_report`: present with all required fields
  - `evidence_registry`: present and populated
- No downstream consumer code changes are needed.

---

## Scenario 5 — Malformed Input → Validation Report Catches All (SC-005, US-6)

**Verify**: A KU with no EvidenceReference, a KR referencing a non-existent unit id,
and a KU with an unrecognized type are all caught in the Validation Report with zero
violations silently reaching the package.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_validator.py::test_malformed_inputs_caught -v
```

**Setup**: Post-process `chunk_set_malformed` extraction results to inject:
1. A `KnowledgeUnit` with `evidence_references = ()` (empty tuple).
2. A `KnowledgeRelationship` with `source_unit_id = "ku_nonexistent_id"`.
3. A `KnowledgeUnit` with `type = "unknown_type"` (force-constructed via `model_construct`).

**Expected outcomes**:
- `validation_report.status == "failed"` (at least one error).
- `validation_report.errors` contains a `ValidationRuleResult` for `"evidence_non_empty"`.
- `validation_report.errors` contains a `ValidationRuleResult` for `"dangling_unit_reference"`.
- `validation_report.errors` contains a `ValidationRuleResult` for `"recognized_unit_type"`.
- None of the three injected violations is present in the final `knowledge_units` or
  `knowledge_relationships` of the returned package.

---

## Scenario 6 — Two Representation Strategies, Package Unchanged (SC-006, US-5)

**Verify**: Applying two different Representation Strategies to the same KnowledgePackage
produces two different output formats; the package is identical before and after both.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_assembler.py::test_representation_strategy_no_mutation -v
```

**Setup**: Register a `GraphRepresentationStub` (returns `dict` with "nodes"/"edges" keys)
and a `RelationalRepresentationStub` (returns `list[dict]`). Apply both to a fixture
`KnowledgePackage`.

**Expected outcomes**:
- `graph_result` has keys `"nodes"` and `"edges"`.
- `relational_result` is a `list`.
- `package_before == package_after_graph == package_after_relational` (equality check on
  `package.metadata.package_id` and all contained entity ids).
- No `KnowledgeUnit` or `KnowledgeRelationship` field is mutated.

---

## Scenario 7 — No External Infrastructure Required (SC-007)

**Verify**: The pipeline runs to completion without invoking any embedding call, vector
store call, graph database query, or retrieval engine call.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_structural_extractor.py::test_no_external_calls -v
```

**Setup**: Wrap the pipeline execution with a mock that raises if any external HTTP call
is made (use `respx` or `unittest.mock.patch` on `httpx.AsyncClient`).

**Expected outcomes**:
- Pipeline completes without the mock raising.
- A valid `KnowledgePackage` is returned.
- `validation_report.status` is `"passed"` or `"passed_with_warnings"`.

---

## Scenario 8 — Knowledge Normalization: Alias Deduplication (SC-010, US-4)

**Verify**: Two raw KUs with the same concept under different surface forms are merged
into one canonical KU whose `evidence_references` includes both source chunks.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_rule_based_normalizer.py::test_alias_deduplication -v
```

**Setup**: Use `chunk_set_alias_pair` (two chunks: "ASA" and "acetylsalicylic acid").
Configure `normalizer_params.alias_map: {"asa": "acetylsalicylic acid"}`.

**Expected outcomes**:
- After normalization: 1 canonical `KnowledgeUnit` (not 2).
- `ku.evidence_references` contains references to both original chunks.
- `ku.attributes["aliases"]` includes `"asa"` (or the original surface form).
- No evidence is discarded.

---

## Scenario 9 — KU Immutability Enforcement (SC-011)

**Verify**: Any attempt to modify a published KnowledgeUnit raises an error.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_models.py::test_knowledge_unit_immutability -v
```

**Expected outcomes**:
- `ku.type = "definition"` raises `ValidationError` (Pydantic frozen model).
- `ku.semantic_content["key"] = "new"` raises `TypeError` (dict on frozen model is
  read-only if model itself is frozen; otherwise test via `ku = ku.model_copy(update={"type": "definition"})` → new `ku2` has new id).
- `ku.id` remains unchanged; `ku2.id != ku.id` when content differs.

---

## Scenario 10 — Relationship Discovery Sub-Pipeline Testability (SC-012)

**Verify**: The candidate set contains at least one candidate that does not survive
validation, confirming the two sub-stages operate independently.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_structural_discoverer.py::test_validation_filters_dangling -v
```

**Setup**: Use `chunk_set_malformed`. Force-inject a `RelationshipCandidate` referencing
a `source_unit_id` that does not exist in the Normalized KU set.

**Expected outcomes**:
- `candidates` list from `generate_candidates()` contains the dangling-reference candidate.
- `relationships` list from `validate_candidates()` does NOT contain that candidate.
- The final `KnowledgePackage` has no relationship with the dangling source id.

---

## Scenario 11 — NER Strategy Swappability (SC-009)

**Verify**: Configuring a NER extraction strategy produces entity-type KUs; switching back
to the default produces non-entity KUs; in both cases, package structure is identical.

**Run**:
```bash
pytest tests/unit/core/knowledge/test_structural_extractor.py::test_ner_strategy_swappability -v
```

**Setup**: Register a `StubNERExtractor` that produces `KnowledgeUnit` with `type == "fact"`
(entity-compatible) and a `"source": "ner"` in `attributes`. Use `chunk_set_ner_compatible`.

**Expected outcomes**:
- With `extractor_strategy: "stub_ner"`: all KUs have `attributes["source"] == "ner"`.
- With `extractor_strategy: "structural"`: all KUs have `attributes["source"] != "ner"`.
- Both packages have identical structural shapes (same fields present, same types valid).
- `KnowledgeValidationReport` structure is identical in both cases.

---

## End-to-End Integration Test (All SCs)

**Run** (requires Docker + PostgreSQL):
```bash
pytest tests/integration/test_knowledge_pipeline_e2e.py -v
```

This test:
1. Creates a fixture `ChunkSet` with `chunk_set_five_forms`.
2. Runs the full `KnowledgeRepresentationPipeline` using default strategies.
3. Persists the `KnowledgePackage` via `KnowledgePackageRepository`.
4. Retrieves the persisted package and compares to the in-memory package.
5. Verifies all SC-001–SC-007 expectations in a single run.
6. Measures wall time and asserts ≤ 2× chunking baseline (latency recorded as a skippable
   assertion; run with `--benchmark` to enforce).

---

## References

- Data model: [data-model.md](data-model.md)
- Interface contracts: [contracts/pipeline-contract.md](contracts/pipeline-contract.md)
- Feature spec: [spec.md](spec.md)
- Research decisions: [research.md](research.md)
