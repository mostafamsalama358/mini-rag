# Knowledge Representation Pipeline Contract

**Feature**: `008-knowledge-representation` | **Date**: 2026-07-13

This document defines the stable interface contracts for the four pluggable components of
the Knowledge Representation pipeline and the shape of the terminal `KnowledgePackage`
output. Any implementation that satisfies these contracts is a valid participant in the
pipeline without core modification.

---

## 1. Pipeline Input Contract

**Type**: `ChunkSet` (from `src/core/chunking/models.py`, spec 007)

The pipeline accepts exactly one `ChunkSet` per run. The ChunkSet must be the validated
output of `007-intelligent-chunking-engine`.

**Required fields on ChunkSet**:
- `chunks`: non-empty ordered list of `Chunk` objects
- `validation_report.status`: not `"fail"` (degraded input is accepted but logged)
- `asset_id`: non-empty string
- `strategy_id`: non-empty string

**Required fields on each Chunk**:
- `identity.chunk_id`: stable, non-empty
- `identity.document_id`: non-empty (= Document Model id)
- `identity.source_element_ids`: non-empty list
- `structural_context.element_type`: a recognized `StructuralElementType` value
- `text`: may be empty only for `figure-placeholder` type

The pipeline does not re-parse documents, re-run chunking, or access any storage layer
during execution.

---

## 2. KnowledgeUnitExtractor Interface Contract

**ABC**: `src/core/knowledge/interfaces.py::KnowledgeUnitExtractor`

```
Input:  (chunk_set: ChunkSet, config: KnowledgeExtractionConfig)
Output: list[KnowledgeUnit]                                        # one or more per Chunk
```

**Guarantees the implementor MUST provide**:
- Every returned `KnowledgeUnit` has a non-empty `evidence_references` collection.
- Every `EvidenceReference` in every unit carries all four traceability levels.
- Every returned unit has a `type` from `KnowledgeUnitType`.
- Every returned unit has a stable `id` derivable from its inputs.
- The extractor MUST NOT invoke LLM inference, embeddings, or external network calls
  unless explicitly documented as an optional non-default strategy.
- The extractor MUST NOT modify any `Chunk` in the `ChunkSet`.

**Guarantees the pipeline provides to implementations**:
- The `ChunkSet` passed to `extract()` is immutable (frozen Pydantic).
- `config.extractor_params` contains only recognized keys for this strategy (validated
  by the factory before dispatch).

---

## 3. KnowledgeNormalizer Interface Contract

**ABC**: `src/core/knowledge/interfaces.py::KnowledgeNormalizer`

```
Input:  (units: list[KnowledgeUnit], config: KnowledgeExtractionConfig)
Output: list[KnowledgeUnit]                                        # normalized set
```

**Guarantees the implementor MUST provide**:
- Output count ≤ input count (normalization may merge but never creates new semantic units).
- For every merged unit, the output unit's `evidence_references` is the union of all merged
  input units' `evidence_references` (no evidence discarded, FR-023c).
- The output list contains no duplicate `id` values.
- No `EvidenceReference` in any input unit is modified.
- No `KnowledgeRelationship` is created.
- No new semantic meaning is introduced.

**Hard constraints** (FR-023):
- MUST NOT create new KUs other than canonical replacements for detected duplicates.
- MUST NOT infer new knowledge claims.
- MUST NOT discard any `EvidenceReference` from merged units.

---

## 4. RelationshipDiscoverer Interface Contract

**ABC**: `src/core/knowledge/interfaces.py::RelationshipDiscoverer`

### Sub-stage 1 — generate_candidates

```
Input:  (units: list[KnowledgeUnit], chunk_set: ChunkSet,
         config: KnowledgeExtractionConfig)
Output: list[RelationshipCandidate]
```

**Guarantees**:
- Every candidate has a non-empty `evidence_references` collection.
- `source_unit_id` and `target_unit_id` reference ids in the provided `units` list
  (may still be invalid — validation filters them).
- Candidates are intermediate and MUST NOT be included in the final KnowledgePackage.
- Knowledge Units MUST NOT be modified.

### Sub-stage 2 — validate_candidates

```
Input:  (candidates: list[RelationshipCandidate], units: list[KnowledgeUnit],
         config: KnowledgeExtractionConfig)
Output: list[KnowledgeRelationship]
```

**Guarantees**:
- Every returned `KnowledgeRelationship` has `source_unit_id` and `target_unit_id` that
  exist in `units`.
- No self-referencing relationships (`source != target`).
- Every returned relationship has a non-empty `evidence_references` collection.
- Knowledge Units MUST NOT be modified.
- `RelationshipCandidate` objects are discarded after this stage.

---

## 5. KnowledgeRepresentationStrategy Interface Contract

**Protocol**: `src/core/knowledge/interfaces.py::KnowledgeRepresentationStrategy`

```
Input:  (package: KnowledgePackage)
Output: Any                           # strategy-specific representation artifact
```

**Guarantees the implementor MUST provide**:
- The `KnowledgePackage` is identical before and after `apply()` — no field is modified
  (verified by equality check in tests, FR-028, SC-006).
- No new `KnowledgeUnit` or `KnowledgeRelationship` is created.
- No `EvidenceReference` is modified or introduced.
- No persistence, indexing, or embedding is performed inside `apply()`.
- `apply()` is a pure function: same `KnowledgePackage` → same output artifact.

---

## 6. KnowledgePackage Output Contract

**Type**: `KnowledgePackage` (from `src/core/knowledge/models.py`)

The pipeline's terminal output satisfies the following structural guarantees for all
downstream consumers:

| Guarantee | Description |
|-----------|-------------|
| Non-empty units | `knowledge_units` contains at least one `KnowledgeUnit` for any non-empty ChunkSet |
| Full evidence chain | Every KU and KR has a non-empty `evidence_references`; every ref carries all four traceability levels |
| Immutability | All fields are frozen; assignment raises immediately |
| Idempotency | Same ChunkSet + config → same `metadata.package_id` and same content |
| Validation report | `validation_report` is always present and structurally complete |
| Evidence registry | `evidence_registry` indexes every `EvidenceReference` referenced by any KU or KR |
| Representation-agnostic | No graph structure, embeddings, or representation-format-specific fields are embedded in the package |
| Strategy fingerprints | `metadata` carries all three applied strategy ids and `config_hash` for reproducibility |

---

## 7. Configuration Contract (KnowledgeExtractionConfig)

**Type**: `KnowledgeExtractionConfig` (from `src/core/knowledge/models.py`)

Loaded from pack YAML following generic < domain < project precedence (FR-002).
YAML key: `knowledge_representation` within the active field pack.

**Example YAML** (in `src/fields/generic/knowledge_representation.yaml`):

```yaml
knowledge_representation:
  extractor_strategy: structural
  normalizer_strategy: rule_based
  discoverer_strategy: structural
  representation_strategies: []
  max_units: null
  extractor_params: {}
  normalizer_params:
    alias_map: {}
  discoverer_params: {}
```

Domain packs (e.g., `src/fields/pharmacy/knowledge_representation.yaml`) override
only the keys that differ, following the existing pack precedence pattern.
