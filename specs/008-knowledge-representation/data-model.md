# Data Model: Knowledge Representation

**Feature**: `008-knowledge-representation` | **Date**: 2026-07-13

All new Pydantic models live in `src/core/knowledge/models.py` unless otherwise noted.
All published models use `ConfigDict(frozen=True)` (immutability, research R1).
Interface ABCs and Protocols live in `src/core/knowledge/interfaces.py`.

---

## 0. Enumerations

### KnowledgeUnitType

```python
KnowledgeUnitType = Literal[
    "fact",
    "procedure",
    "rule",
    "definition",
    "measurement",
    "list",
    "table",
    "assertion",
    "structured_observation",
]
```

Vocabulary from FR-005. Extensible: new literal values may be added without changing
the model shape. A value not in this set is an error caught by `KnowledgeValidator`.

### KnowledgeRelationshipType

```python
KnowledgeRelationshipType = Literal[
    "dependency",
    "equivalence",
    "contradiction",
    "elaboration",
    "containment",
    "sequence",
    "derivation",
]
```

Vocabulary from FR-010. Extensible with additional types as additive vocabulary
extensions.

### KnowledgeValidationStatus

```python
KnowledgeValidationStatus = Literal["passed", "passed_with_warnings", "failed"]
```

### ValidationRuleOutcome

```python
ValidationRuleOutcome = Literal["pass", "error", "warning"]
```

---

## 1. EvidenceReference

**File**: `src/core/knowledge/models.py`

The complete, four-level traceability record linking a Knowledge Unit or Knowledge
Relationship to its source evidence (FR-013, FR-014).

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | `"er_" + SHA256(canonical_payload)[:16]` (research R2) |
| `chunk_ids` | `list[str]` | One or more Chunk ids from the input ChunkSet; non-empty |
| `element_ids` | `list[str]` | One or more Structural Element ids from the DocumentModel; non-empty |
| `document_model_id` | `str` | Identity of the Canonical Document Model (from `006`) |
| `asset_id` | `str` | Identity of the original document/asset |

**Validation rules**:
- All four traceability levels must be non-empty; a partial `EvidenceReference` is
  invalid (FR-014). `KnowledgeValidator` catches references with empty lists.
- `id` is derived deterministically from `sorted(chunk_ids)`, `sorted(element_ids)`,
  `document_model_id`, `asset_id` (research R2).
- Immutable once constructed (`frozen=True`).

---

## 2. KnowledgeUnit

**File**: `src/core/knowledge/models.py`

The primary semantic entity of the Knowledge Representation stage. The smallest
independently meaningful semantic representation built from one or more Chunks (FR-004).

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | `"ku_" + SHA256(canonical_payload)[:16]` (research R2) |
| `type` | `KnowledgeUnitType` | Semantic type from supported vocabulary (FR-005) |
| `semantic_content` | `dict[str, Any]` | Typed structure per KU type (research R8); never constrained to RDF triple form (FR-006) |
| `participants` | `dict[str, Any] \| None` | Named roles where applicable (research R9); `None` when not applicable |
| `attributes` | `dict[str, Any]` | Qualifiers, units, temporal scope, confidence (when probabilistic), surface aliases; always includes `"source_surface_form"` (research R9) |
| `evidence_references` | `tuple[EvidenceReference, ...]` | Non-empty collection of EvidenceReference entities; `tuple` enforces immutability on the collection (FR-013) |
| `relationships` | `tuple[str, ...]` | Relationship ids involving this unit; populated after Relationship Discovery; read-only on the unit (FR-007) |
| `metadata` | `KnowledgeUnitMetadata` | Extraction strategy id, normalization status, creation timestamp |

**Validation rules**:
- `evidence_references` must be non-empty (FR-013).
- `type` must be a recognized `KnowledgeUnitType` (FR-005); unknown types surface as
  `KnowledgeValidator` errors (FR-024c).
- `id` is stable and deterministic (FR-008): derived from `sorted(evidence_ref_ids)`,
  `type`, `strategy_id`, `config_hash`.
- Immutable once published into a KnowledgePackage: `frozen=True` raises on mutation;
  semantic changes must produce a new KnowledgeUnit with a new id (FR-008a).

---

## 3. KnowledgeUnitMetadata

**File**: `src/core/knowledge/models.py`

Non-semantic bookkeeping attached to every KnowledgeUnit.

| Field | Type | Notes |
|-------|------|-------|
| `extractor_strategy_id` | `str` | Registered name of the extraction strategy that produced this unit |
| `normalization_status` | `Literal["raw", "normalized", "merged"]` | `"raw"` before normalization; `"normalized"` after; `"merged"` if this unit is the canonical result of deduplication |
| `created_at` | `str` | ISO 8601 UTC timestamp of unit creation |
| `config_hash` | `str` | 8-char hash of the `KnowledgeExtractionConfig` (for id stability) |

---

## 4. KnowledgeRelationship

**File**: `src/core/knowledge/models.py`

A first-class, typed semantic relationship between two Knowledge Units (FR-009).
Not an implicit graph edge — an independently traceable entity with its own id and
EvidenceReference collection.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | `"kr_" + SHA256(canonical_payload)[:16]` (research R2) |
| `relationship_type` | `KnowledgeRelationshipType` | Semantic type from supported vocabulary (FR-010) |
| `source_unit_id` | `str` | Id of the source Knowledge Unit |
| `target_unit_id` | `str` | Id of the target Knowledge Unit |
| `evidence_references` | `tuple[EvidenceReference, ...]` | Non-empty collection; supports inferred relationships referencing source/target chunks (FR-009) |
| `attributes` | `dict[str, Any]` | Directionality (`"directed"` or `"undirected"`); optional confidence qualifier when from a probabilistic strategy; temporal scope |
| `metadata` | `KnowledgeRelationshipMetadata` | Producing strategy id, creation timestamp |

**Validation rules**:
- `evidence_references` must be non-empty (FR-013).
- `source_unit_id` and `target_unit_id` must both exist in the containing KnowledgePackage;
  dangling references are caught by `KnowledgeValidator` (FR-011, FR-024b).
- `source_unit_id != target_unit_id` (no self-referencing relationships).
- Immutable once published: `frozen=True` (FR-009a).

---

## 5. KnowledgeRelationshipMetadata

**File**: `src/core/knowledge/models.py`

Non-semantic bookkeeping for a KnowledgeRelationship.

| Field | Type | Notes |
|-------|------|-------|
| `discoverer_strategy_id` | `str` | Registered name of the Relationship Discovery strategy |
| `created_at` | `str` | ISO 8601 UTC timestamp |

---

## 6. RelationshipCandidate

**File**: `src/core/knowledge/models.py`

An intermediate entity produced by Relationship Candidate Discovery — Sub-stage 1 of the
Relationship Discovery sub-pipeline (FR-023d). **Not included** in the final
KnowledgePackage; consumed and discarded by Relationship Validation.

| Field | Type | Notes |
|-------|------|-------|
| `source_unit_id` | `str` | Proposed source Knowledge Unit id |
| `target_unit_id` | `str` | Proposed target Knowledge Unit id |
| `relationship_type` | `KnowledgeRelationshipType` | Proposed relationship type |
| `evidence_references` | `tuple[EvidenceReference, ...]` | Supporting evidence; non-empty |
| `rationale` | `str` | Human-readable explanation of why this candidate was generated |
| `score` | `float \| None` | Optional strategy-specific score; present only for probabilistic strategies; `None` for deterministic strategies |

**Note**: `RelationshipCandidate` uses `frozen=False` — it is a mutable intermediate
entity, not a published artifact. It is discarded after Relationship Validation completes.

---

## 7. ValidationRuleResult

**File**: `src/core/knowledge/models.py`

Per-rule outcome record in the `KnowledgeValidationReport` (FR-025).

| Field | Type | Notes |
|-------|------|-------|
| `rule_id` | `str` | Named quality rule identifier (see named rules table below) |
| `outcome` | `ValidationRuleOutcome` | `"pass"`, `"error"`, or `"warning"` |
| `implicated_unit_ids` | `list[str]` | Knowledge Unit ids that triggered this outcome; empty for `"pass"` |
| `implicated_relationship_ids` | `list[str]` | Knowledge Relationship ids involved; empty when not applicable |
| `message` | `str` | Human-readable description of the outcome |

**Named quality rules** (FR-024):

| `rule_id` | Outcome type | What is checked |
|-----------|-------------|-----------------|
| `evidence_non_empty` | error | Every KU and KR has a non-empty `evidence_references` collection |
| `reference_resolution` | error | Every Chunk id and Element id in every EvidenceReference exists in the input ChunkSet / DocumentModel |
| `dangling_unit_reference` | error | Every `source_unit_id` and `target_unit_id` in every KR exists in the package |
| `recognized_unit_type` | error | Every KU has a type value from the supported vocabulary |
| `full_traceability_chain` | error | Every EvidenceReference carries all four required levels (chunk_ids, element_ids, document_model_id, asset_id) |
| `max_unit_count_exceeded` | warning | Unit count exceeds configured maximum (if set in pack YAML) |
| `unit_without_semantic_content` | warning | KU has an empty or null `semantic_content` dict |

---

## 8. KnowledgeValidationReport

**File**: `src/core/knowledge/models.py`

The formal structured outcome of Knowledge Validation — an immutable audit artifact
(FR-025). Produced exactly once per pipeline run. Retained independently of the
KnowledgePackage for observability (FR-026).

| Field | Type | Notes |
|-------|------|-------|
| `status` | `KnowledgeValidationStatus` | Overall outcome: `"passed"`, `"passed_with_warnings"`, or `"failed"` |
| `errors` | `tuple[ValidationRuleResult, ...]` | Blocking rule violations; non-empty when `status == "failed"` |
| `warnings` | `tuple[ValidationRuleResult, ...]` | Non-blocking observations |
| `validation_results` | `tuple[ValidationRuleResult, ...]` | All per-rule outcomes (errors + warnings + passes) |
| `statistics` | `KnowledgeValidationStatistics` | Counts derived from the validation run |
| `metadata` | `KnowledgeValidationMetadata` | Run identity, timestamp, rule set version |

**Validation rules**:
- Immutable once produced: `frozen=True`.
- `status` MUST be `"failed"` when `errors` is non-empty.
- `status` MUST be `"passed_with_warnings"` when `errors` is empty and `warnings` is non-empty.
- `status` MUST be `"passed"` when both are empty.

---

## 9. KnowledgeValidationStatistics

| Field | Type | Notes |
|-------|------|-------|
| `total_units_checked` | `int` | Total number of KnowledgeUnits inspected |
| `total_relationships_checked` | `int` | Total number of KnowledgeRelationships inspected |
| `error_count` | `int` | Number of `"error"` outcomes across all rules |
| `warning_count` | `int` | Number of `"warning"` outcomes across all rules |
| `auto_correction_count` | `int` | Number of auto-corrections applied (e.g., dropped dangling KRs) |

---

## 10. KnowledgeValidationMetadata

| Field | Type | Notes |
|-------|------|-------|
| `chunk_set_id` | `str` | `asset_id` of the originating ChunkSet |
| `knowledge_package_id` | `str` | Id of the KnowledgePackage being validated |
| `validated_at` | `str` | ISO 8601 UTC timestamp |
| `rule_set_version` | `str` | Semantic version of the quality rule set applied (e.g., `"1.0.0"`) |

---

## 11. KnowledgePackageMetadata

| Field | Type | Notes |
|-------|------|-------|
| `package_id` | `str` | `"kp_" + SHA256("{asset_id}|{extractor_id}|{normalizer_id}|{discoverer_id}|{config_hash}")[:16]` |
| `chunk_set_asset_id` | `str` | `asset_id` from the input `ChunkSet` |
| `document_model_id` | `str` | Identity of the Canonical Document Model |
| `asset_id` | `str` | Identity of the original document |
| `extractor_strategy_id` | `str` | Registered name of the KnowledgeUnitExtractor used |
| `normalizer_strategy_id` | `str` | Registered name of the KnowledgeNormalizer used |
| `discoverer_strategy_id` | `str` | Registered name of the RelationshipDiscoverer used |
| `config_hash` | `str` | 8-char hash of the `KnowledgeExtractionConfig` |
| `created_at` | `str` | ISO 8601 UTC timestamp |

---

## 12. KnowledgePackageStatistics

| Field | Type | Notes |
|-------|------|-------|
| `unit_counts_by_type` | `dict[str, int]` | Count of KUs per `KnowledgeUnitType` value |
| `relationship_counts_by_type` | `dict[str, int]` | Count of KRs per `KnowledgeRelationshipType` value |
| `evidence_coverage_pct` | `float` | Fraction of input Chunks referenced by at least one KU's EvidenceReference (`0.0`–`100.0`) |
| `validation_pass_count` | `int` | Quality rules that passed |
| `validation_error_count` | `int` | Quality rules that failed |
| `validation_warning_count` | `int` | Quality rules that produced warnings |

---

## 13. KnowledgePackage

**File**: `src/core/knowledge/models.py`

The stage's terminal output — a validated, self-contained collection of Normalized
Knowledge Units and Knowledge Relationships for one document (FR-017).

| Field | Type | Notes |
|-------|------|-------|
| `knowledge_units` | `tuple[KnowledgeUnit, ...]` | Ordered collection of Normalized KUs (document reading order preserved) |
| `knowledge_relationships` | `tuple[KnowledgeRelationship, ...]` | All typed, validated Knowledge Relationships |
| `evidence_registry` | `dict[str, EvidenceReference]` | Consolidated index: `{er_id: EvidenceReference}` for all EvidenceReferences in the package; supports O(1) lookup (FR-017) |
| `validation_report` | `KnowledgeValidationReport` | Always present; immutable audit artifact |
| `metadata` | `KnowledgePackageMetadata` | Package-level identity and strategy fingerprints |
| `statistics` | `KnowledgePackageStatistics` | Derived counts and coverage metrics |

**Validation rules**:
- Immutable once published: `frozen=True` (FR-017a).
- `validation_report` is always present, even for packages that passed with zero violations.
- Every `EvidenceReference` id referenced by any KU or KR MUST be a key in `evidence_registry`.
- Re-running the same pipeline on the same unchanged ChunkSet with the same config MUST
  produce a KnowledgePackage with the same `metadata.package_id` (idempotency, FR-019).

---

## 14. KnowledgeExtractionConfig

**File**: `src/core/knowledge/models.py`

Configuration for a single pipeline run, loaded from pack YAML following
generic < domain < project precedence (FR-002, `002-field-registry`).

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `extractor_strategy` | `str` | `"structural"` | Registered `KnowledgeUnitExtractor` name |
| `normalizer_strategy` | `str` | `"rule_based"` | Registered `KnowledgeNormalizer` name |
| `discoverer_strategy` | `str` | `"structural"` | Registered `RelationshipDiscoverer` name |
| `representation_strategies` | `list[str]` | `[]` | Zero or more registered `KnowledgeRepresentationStrategy` names to apply post-assembly |
| `max_units` | `int \| None` | `None` | Optional upper bound on KU count; excess triggers a validation warning |
| `extractor_params` | `dict[str, Any]` | `{}` | Strategy-specific configuration for the extractor |
| `normalizer_params` | `dict[str, Any]` | `{}` | Strategy-specific configuration for the normalizer |
| `discoverer_params` | `dict[str, Any]` | `{}` | Strategy-specific configuration for the discoverer |

---

## 15. Strategy Interfaces

**File**: `src/core/knowledge/interfaces.py`

### KnowledgeUnitExtractor (ABC)

```python
class KnowledgeUnitExtractor(ABC):
    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @abstractmethod
    def extract(
        self,
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]: ...
```

One registered implementation = one pluggable extraction strategy (FR-020). The default
`"structural"` strategy is `StructuralKnowledgeUnitExtractor` (research R3).

### KnowledgeNormalizer (ABC)

```python
class KnowledgeNormalizer(ABC):
    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @abstractmethod
    def normalize(
        self,
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]: ...
```

One implementation = one pluggable normalization strategy (FR-023a). The default
`"rule_based"` strategy is `RuleBasedKnowledgeNormalizer` (research R4).

**Contract**: The output list must satisfy the normalization hard constraints (FR-023):
- No new semantic meaning introduced.
- No new knowledge claims inferred.
- No new KUs created beyond canonical replacements for detected duplicates.
- No KRs created.
- No EvidenceReferences modified.
- No evidence discarded from merged units.

### RelationshipDiscoverer (ABC)

```python
class RelationshipDiscoverer(ABC):
    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @abstractmethod
    def generate_candidates(
        self,
        units: list[KnowledgeUnit],
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[RelationshipCandidate]: ...

    @abstractmethod
    def validate_candidates(
        self,
        candidates: list[RelationshipCandidate],
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeRelationship]: ...
```

The two-method interface enforces the two-stage sub-pipeline (FR-023d). Both methods
are independently testable. `RelationshipCandidate` entities are intermediate; only
`KnowledgeRelationship` objects from `validate_candidates` enter the package (FR-023e).

### KnowledgeRepresentationStrategy (Protocol)

```python
class KnowledgeRepresentationStrategy(Protocol):
    @property
    def strategy_id(self) -> str: ...

    def apply(
        self,
        package: KnowledgePackage,
    ) -> Any: ...
```

A pure read-only projection (FR-027a). Must not modify `package` or any of its contents.
Must not create new KUs, KRs, or EvidenceReferences. Must not perform persistence.
The return type `Any` is deliberately broad — each strategy produces its own representation
artifact (Knowledge Graph structure, relational table, etc.).

---

## 16. KnowledgeRepresentationPipeline

**File**: `src/core/knowledge/pipeline.py`

Orchestrator that wires the four stages. Not a model — an application-layer class.

```python
class KnowledgeRepresentationPipeline:
    def __init__(
        self,
        extractor: KnowledgeUnitExtractor,
        normalizer: KnowledgeNormalizer,
        discoverer: RelationshipDiscoverer,
        representation_strategies: list[KnowledgeRepresentationStrategy],
        validator: KnowledgeValidator,
        assembler: KnowledgePackageAssembler,
    ) -> None: ...

    def run(
        self,
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> KnowledgePackage: ...
```

`run()` executes the six-stage sequence:
1. Extraction → raw `list[KnowledgeUnit]`
2. Normalization → normalized `list[KnowledgeUnit]`
3. Relationship Candidate Discovery → `list[RelationshipCandidate]`
4. Relationship Validation → `list[KnowledgeRelationship]`
5. Assembly → draft `KnowledgePackage`
6. Validation → `KnowledgeValidationReport` → final `KnowledgePackage`

Representation strategies are applied post-assembly if configured (FR-027). The pipeline
returns the `KnowledgePackage`; representation artifacts are returned separately or
discarded at the caller's discretion.

---

## Entity Relationship Summary

```
ChunkSet (from 007) ──────────────────────┐
  Chunk (N)                               │
    ChunkIdentity.chunk_id                │
    ChunkRelationships                    │
    ChunkLineage.source_element_ids       │
    StructuralContext.element_type        │
                                          ▼
                         KnowledgeUnitExtractor.extract()
                                          │
                                          ▼
                              list[KnowledgeUnit] (raw)
                                          │
                         KnowledgeNormalizer.normalize()
                                          │
                                          ▼
                         list[KnowledgeUnit] (normalized)
                                  │              │
       RelationshipDiscoverer.generate_candidates()
                                          │
                                          ▼
                         list[RelationshipCandidate]
                                          │
       RelationshipDiscoverer.validate_candidates()
                                          │
                                          ▼
                         list[KnowledgeRelationship]
                                          │
                                          ▼
                         KnowledgePackageAssembler.assemble()
                                          │
                                          ▼
                              KnowledgePackage (draft)
                                          │
                         KnowledgeValidator.validate()
                                          │
                                    ┌─────┴─────┐
                                    ▼           ▼
                    KnowledgeValidationReport   KnowledgePackage (final, immutable)
                                                        │
                         KnowledgeRepresentationStrategy.apply() (optional, N strategies)
                                                        │
                                                        ▼
                                         Representation artifact(s) (read-only projections)

KnowledgeUnit ──has──> tuple[EvidenceReference, ...]
KnowledgeRelationship ──has──> tuple[EvidenceReference, ...]
KnowledgePackage.evidence_registry ──indexes──> all EvidenceReferences (by er_id)
KnowledgePackage.validation_report ──is──> KnowledgeValidationReport
```

---

## Module File Map

| File | Contents |
|------|----------|
| `src/core/knowledge/models.py` | All Pydantic models above (sections 0–14) |
| `src/core/knowledge/interfaces.py` | `KnowledgeUnitExtractor`, `KnowledgeNormalizer`, `RelationshipDiscoverer`, `KnowledgeRepresentationStrategy` |
| `src/core/knowledge/pipeline.py` | `KnowledgeRepresentationPipeline`, `KnowledgePackageAssembler` orchestration |
| `src/core/knowledge/assembly.py` | `KnowledgePackageAssembler` implementation |
| `src/core/knowledge/validation.py` | `KnowledgeValidator` + named quality rule implementations |
| `src/core/knowledge/registry.py` | `ExtractorRegistry`, `NormalizerRegistry`, `DiscovererRegistry`, `RepresentationStrategyRegistry` |
| `src/core/knowledge/errors.py` | `KnowledgeRepresentationError`, `EvidenceIntegrityError`, `StrategyNotFoundError`, `KnowledgeValidationFailedError` |
| `src/core/knowledge/extractors/structural.py` | `StructuralKnowledgeUnitExtractor` |
| `src/core/knowledge/normalizers/rule_based.py` | `RuleBasedKnowledgeNormalizer` |
| `src/core/knowledge/discovery/structural.py` | `StructuralRelationshipDiscoverer` |
| `src/core/knowledge/discovery/validator.py` | `RelationshipCandidateValidator` (internal helper) |
| `src/core/knowledge/representation/base.py` | Re-exports `KnowledgeRepresentationStrategy` |
| `src/tasks/knowledge_representation.py` | Celery task `run_knowledge_representation` |
