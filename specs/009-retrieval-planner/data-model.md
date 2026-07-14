# Data Model: Retrieval Planner

**Feature**: `009-retrieval-planner` | **Date**: 2026-07-14

All new Pydantic models live in `src/core/retrieval_planner/models.py` unless otherwise noted.
All published models use `ConfigDict(frozen=True)` (immutability, research R3).
Interface ABCs live in `src/core/retrieval_planner/interfaces.py`.

---

## 0. Open Types and Enumerations

### StrategyType

```python
from typing import Annotated
from pydantic import Field

StrategyType = Annotated[str, Field(min_length=1)]
```

An open, non-exhaustive string-backed type. Not a closed `Literal` or `Enum`.
Available values for a domain are declared in the field pack YAML under
`retrieval_planning.available_strategies`. The initial vocabulary (FR-014):

```
semantic  keyword  metadata  graph  document  section  table  hybrid  mixed
```

New values are added via field pack YAML with zero Planner code changes (SC-010, research R2).

---

### IntentCategory

```python
IntentCategory = Literal[
    "factual",
    "list",
    "comparative",
    "procedural",
    "tabular",
    "navigational",
    "mixed",
]
```

Closed for the default classifier. New categories require a code addition to the
`RuleBasedIntentClassifier` and a corresponding entry in the field pack strategy mapping
table. This is a controlled extension point, not an open vocabulary.

---

### OutputShapeType

```python
OutputShapeType = Literal[
    "single_fact",
    "list",
    "summary",
    "table",
    "comparison",
    "narrative",
]
```

---

## 1. QueryIntent

The enriched, classified representation of what the user wants to retrieve (FR-002).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `category` | `IntentCategory` | Primary classified intent |
| `confidence` | `float` | 0.0–1.0; produced by `IIntentClassifier`; drives clarification gate (research R9) |
| `secondary_categories` | `tuple[IntentCategory, ...]` | Other plausible intents in confidence order; used to generate clarification questions |
| `evidence` | `tuple[str, ...]` | Phrases/tokens from `canonical_query` that drove this classification |

**Validation rules**:
- `confidence` in `[0.0, 1.0]`.
- `secondary_categories` does not contain `category`.
- Immutable (`frozen=True`).

---

## 2. ResolvedEntity

A named entity extracted from the query, canonicalized and typed (FR-003).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `entity_id` | `str` | `"ent_" + SHA256(f"{canonical_form}\|{entity_type}")[:16]` (research R6) |
| `raw_text` | `str` | Original text span from `ParseResult.query_plan.entities` |
| `canonical_form` | `str` | Resolved canonical name; from field pack alias table, or equals `raw_text` if no alias found |
| `entity_type` | `str` | Open string type (e.g., `"drug"`, `"document"`, `"section"`, `"concept"`); assigned by keyword-pattern table in field pack YAML |
| `source_span` | `tuple[int, int] \| None` | Character offsets `(start, end)` in `canonical_query`; `None` if not determinable |

**Validation rules**:
- `raw_text` non-empty.
- `canonical_form` non-empty.
- Immutable (`frozen=True`).

---

## 3. QueryFilter

A structured filter derived from the query (FR-004).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `filter_id` | `str` | `"flt_" + SHA256(f"{filter_type}\|{field_name}\|{operator}\|{str(value)}")[:16]` |
| `filter_type` | `str` | Open string type: `"date"`, `"category"`, `"document_type"`, `"language"`, `"field"`, `"status"`, etc. |
| `field_name` | `str` | Logical field name in the document domain (e.g., `"publication_date"`, `"language"`) |
| `operator` | `str` | Comparison operator: `"eq"`, `"neq"`, `"lt"`, `"gt"`, `"lte"`, `"gte"`, `"in"`, `"not_in"`, `"contains"`, `"range"` |
| `value` | `Any` | Filter value; type depends on `filter_type` and `operator` |
| `source` | `Literal["explicit", "implicit"]` | `"explicit"` = stated in query; `"implicit"` = inferred from context (e.g., language) |

**Validation rules**:
- `field_name` non-empty.
- `operator` in the supported set.
- Immutable (`frozen=True`).

---

## 4. RetrievalLimits

Generic execution bounds expressing *how much* the engine may retrieve (FR-006).
Contains no algorithm-specific implementation details (FR-017, spec revision item 1).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `max_evidence_units` | `int` | Maximum evidence units the Retrieval Engine may return; derived from intent + field pack budget table (research R10) |
| `max_candidates` | `int` | Maximum candidate items the engine may consider before downstream ranking or selection; guides engine resource usage without specifying algorithm (spec revision item 1) |
| `scope` | `Literal["narrow", "standard", "broad", "exhaustive"]` | Semantic search breadth; `"narrow"` = focused, `"exhaustive"` = comprehensive scan |

**Validation rules**:
- `max_evidence_units >= 1`.
- `max_candidates >= max_evidence_units`.
- Immutable (`frozen=True`).

---

## 5. RetrievalConstraints

Generic execution constraints the Retrieval Engine must respect (FR-007).
Declared by the Planner; enforced by the engine.

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Default | Notes |
|---|---|---|---|
| `latency_budget_ms` | `int \| None` | from field pack | Max wall time the engine may spend; `None` = no constraint |
| `cost_budget` | `float \| None` | from field pack | Relative cost budget (abstract unit); `None` = no constraint |
| `freshness_window` | `str \| None` | `None` | ISO 8601 duration (e.g., `"P30D"` = last 30 days); engine filters to content within this window |
| `required_language` | `str \| None` | from query | ISO 639-1 code; engine restricts to content in this language; `None` = any language |
| `citation_required` | `bool` | `True` | When `True`, engine MUST return source citations with every evidence unit (Constitution VI.4) |

**Validation rules**:
- `latency_budget_ms`, if set, >= 1.
- `required_language`, if set, is exactly 2 lowercase alpha characters.
- Immutable (`frozen=True`).

---

## 6. ExecutionHints

Optional, engine-agnostic advisory recommendations (FR-018).
All hints are safely ignorable — ignoring any or all MUST NOT change retrieval correctness
(spec revision item 2). Set to `None` on the plan when no hints are triggered.

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Default | Notes |
|---|---|---|---|
| `preferred_document_types` | `list[str] \| None` | `None` | Document type labels engine should prioritize (e.g., `["clinical_trial", "monograph"]`); advisory |
| `preferred_section_kinds` | `list[str] \| None` | `None` | Section kind labels (e.g., `["dosage", "contraindications"]`); advisory |
| `expand_entities` | `bool \| None` | `None` | Suggests the engine consider entity synonyms or related terms; advisory |
| `allow_table_search` | `bool \| None` | `None` | Suggests the engine include table content in results; advisory |
| `prioritize_recent_content` | `bool \| None` | `None` | Suggests the engine rank more recent documents higher when scores are close; advisory |

**Note**: `ExecutionHints` uses `frozen=False` because it is built incrementally by
`HintsBuilder`. The assembled instance is frozen when embedded in the immutable
`RetrievalPlan`.

---

## 7. OutputShape

The expected shape of the final answer (FR-008). Used by downstream Context Builder
(spec 012) and Answer Generator (spec 013) to format output appropriately.

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `shape_type` | `OutputShapeType` | Primary shape: `"single_fact"`, `"list"`, `"summary"`, `"table"`, `"comparison"`, `"narrative"` |
| `max_items` | `int \| None` | For list/table shapes, the max number of items expected; `None` = unbounded |
| `structured` | `bool` | `True` if answer should be machine-parseable (table/list); `False` for free-text |

**Validation rules**:
- Immutable (`frozen=True`).
- `max_items`, if set, >= 1.

---

## 8. PlannerDiagnostics

Internal debugging metadata (FR-012). Not part of user-visible output. Omitted in
production when `diagnostics_enabled=False` in `RetrievalPlannerConfig`. Set to `None`
on the `RetrievalPlan` when disabled.

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `intent_candidates` | `list[dict[str, Any]]` | All `IntentCategory` candidates with their confidence scores |
| `entity_resolution_trace` | `list[dict[str, Any]]` | Per-entity: `raw_text`, `canonical_form`, `entity_type`, `alias_matched` |
| `strategy_selection_trace` | `list[dict[str, Any]]` | Strategies considered, reason selected/excluded |
| `clarification_trigger` | `str \| None` | Which condition triggered `clarification_required=True`, if applicable |
| `limits_derivation` | `dict[str, Any]` | How `RetrievalLimits` values were computed |
| `planning_latency_ms` | `float` | End-to-end planning wall time (pipeline only) |

`PlannerDiagnostics` does **not** use `frozen=True` — it is an internal assembly
artifact, not a published contract.

---

## 9. RetrievalPlanMetadata

Identity and provenance metadata for a `RetrievalPlan` (research R4, R14).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `plan_id` | `str` | `"rp_" + SHA256(canonical_payload)[:16]` (research R4) |
| `planner_version` | `str` | Semantic version of the Planner implementation (e.g., `"1.0.0"`) |
| `schema_version` | `str` | Semantic version of the `RetrievalPlan` schema (e.g., `"1.0.0"`); checked by engine at startup (SC-011) |
| `config_hash` | `str` | 8-char hash of the `RetrievalPlannerConfig` for id stability |
| `created_at` | `str` | ISO 8601 UTC timestamp |

**Schema versioning policy** (research R14):
- **MAJOR** increment: field removed, renamed, or type-narrowed on any published model.
- **MINOR** increment: new optional field added.
- **PATCH** increment: validation rule or documentation change only.

---

## 10. RetrievalPlan

The terminal, immutable output of the Retrieval Planner. The stable public contract
between the Planner and all downstream specs (010–013) (FR-013, SC-007).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Notes |
|---|---|---|
| `intent` | `QueryIntent` | Classified intent (FR-002) |
| `entities` | `tuple[ResolvedEntity, ...]` | Canonicalized entities; empty if none resolved (FR-003) |
| `filters` | `tuple[QueryFilter, ...]` | Structured filters including implicit language filter (FR-004) |
| `retrieval_strategies` | `tuple[StrategyType, ...]` | Ordered preferred strategies; non-empty unless `clarification_required=True` (FR-005) |
| `retrieval_limits` | `RetrievalLimits` | Generic execution bounds (FR-006) |
| `retrieval_constraints` | `RetrievalConstraints` | Generic execution constraints (FR-007) |
| `execution_hints` | `ExecutionHints \| None` | Advisory hints; `None` if no hints triggered (FR-018) |
| `output_shape` | `OutputShape` | Expected answer shape (FR-008) |
| `clarification_required` | `bool` | When `True`, `retrieval_strategies` is empty and retrieval must not begin (FR-009) |
| `clarification_question` | `str \| None` | Non-empty when `clarification_required=True` (FR-010) |
| `planner_confidence` | `float` | 0.0–1.0; `min(intent.confidence, upstream.confidence)` (FR-011, research R9) |
| `diagnostics` | `PlannerDiagnostics \| None` | Internal; `None` in production; populated when `diagnostics_enabled=True` (FR-012) |
| `metadata` | `RetrievalPlanMetadata` | Plan identity, schema version, provenance |

**Validation rules**:
- When `clarification_required=True`: `clarification_question` is non-empty;
  `retrieval_strategies` is empty; `planner_confidence <= config.clarification_confidence_threshold`.
- When `clarification_required=False`: `retrieval_strategies` is non-empty; `clarification_question` is `None`.
- `planner_confidence` in `[0.0, 1.0]`.
- `RetrievalPlan` contains no retrieval-engine-specific implementation details (FR-017).
- Immutable (`frozen=True`). The `diagnostics` field is frozen as part of the outer model; `PlannerDiagnostics` itself is not frozen prior to assembly.
- Re-running with same input + config produces plan with same `metadata.plan_id` (determinism, NFR-003).

---

## 11. RetrievalPlannerConfig

Configuration for a single planner run, loaded from field pack YAML following
generic < domain < project precedence (spec 002).

**File**: `src/core/retrieval_planner/models.py`

| Field | Type | Default | Notes |
|---|---|---|---|
| `intent_classifier` | `str` | `"rule_based"` | Registered `IIntentClassifier` name |
| `entity_resolver` | `str` | `"query_plan"` | Registered `IEntityResolver` name |
| `filter_extractor` | `str` | `"query_plan"` | Registered `IFilterExtractor` name |
| `strategy_selector` | `str` | `"config_driven"` | Registered `IStrategySelector` name |
| `clarification_detector` | `str` | `"confidence_based"` | Registered `IClarificationDetector` name |
| `available_strategies` | `list[str]` | `["semantic", "keyword", "metadata", "graph", "document", "section", "table", "hybrid", "mixed"]` | Allowed `StrategyType` values for this domain |
| `default_strategy` | `str` | `"semantic"` | Fallback when strategy mapping produces no usable result |
| `clarification_confidence_threshold` | `float` | `0.5` | Below this threshold, clarification is required |
| `strategy_mappings` | `dict[str, list[str]]` | (see research R8) | `IntentCategory → ordered StrategyType list` |
| `budget_defaults` | `dict[str, Any]` | (see research R10) | Intent-keyed budget table |
| `entity_aliases` | `dict[str, str]` | `{}` | `raw_text → canonical_form` alias table |
| `entity_type_patterns` | `list[dict[str, str]]` | `[]` | Pattern-to-entity-type mapping rules |
| `default_latency_budget_ms` | `int \| None` | `None` | Default latency constraint; `None` = no constraint |
| `default_cost_budget` | `float \| None` | `None` | Default cost constraint; `None` = no constraint |
| `citation_required` | `bool` | `True` | Default citation requirement (Constitution VI.4) |
| `diagnostics_enabled` | `bool` | `False` | Populate `PlannerDiagnostics` in production |

---

## 12. Strategy Interfaces

**File**: `src/core/retrieval_planner/interfaces.py`

### IRetrievalPlanner (ABC)

```python
class IRetrievalPlanner(ABC):
    @abstractmethod
    def plan(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> RetrievalPlan: ...
```

The primary entry point. Implementations wire and invoke the full pipeline (research R4).

---

### IIntentClassifier (ABC)

```python
class IIntentClassifier(ABC):
    @property
    @abstractmethod
    def classifier_id(self) -> str: ...

    @abstractmethod
    def classify(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> QueryIntent: ...
```

Default: `RuleBasedIntentClassifier` (research R5).

---

### IEntityResolver (ABC)

```python
class IEntityResolver(ABC):
    @property
    @abstractmethod
    def resolver_id(self) -> str: ...

    @abstractmethod
    def resolve(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> list[ResolvedEntity]: ...
```

Default: `QueryPlanEntityResolver` (research R6).

---

### IFilterExtractor (ABC)

```python
class IFilterExtractor(ABC):
    @property
    @abstractmethod
    def extractor_id(self) -> str: ...

    @abstractmethod
    def extract(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> list[QueryFilter]: ...
```

Default: `QueryPlanFilterExtractor` (research R7).

---

### IStrategySelector (ABC)

```python
class IStrategySelector(ABC):
    @property
    @abstractmethod
    def selector_id(self) -> str: ...

    @abstractmethod
    def select(
        self,
        intent: QueryIntent,
        entities: list[ResolvedEntity],
        filters: list[QueryFilter],
        config: RetrievalPlannerConfig,
    ) -> list[StrategyType]: ...
```

Default: `ConfigDrivenStrategySelector` (research R8).

**Contract**: Must return a non-empty list. If the mapping produces an empty list after
filtering unavailable strategies, must fall back to `[config.default_strategy]`.

---

### IClarificationDetector (ABC)

```python
class IClarificationDetector(ABC):
    @property
    @abstractmethod
    def detector_id(self) -> str: ...

    @abstractmethod
    def detect(
        self,
        parse_result: ParseResult,
        intent: QueryIntent,
        config: RetrievalPlannerConfig,
    ) -> tuple[bool, str | None]: ...
```

Returns `(clarification_required, clarification_question)`. Default:
`ConfidenceBasedClarificationDetector` (research R9).

---

## 13. RetrievalPlannerPipeline

**File**: `src/core/retrieval_planner/pipeline.py`

Stateless orchestrator that wires the six stages into a single `plan()` call.

```python
class RetrievalPlannerPipeline(IRetrievalPlanner):
    def __init__(
        self,
        intent_classifier: IIntentClassifier,
        entity_resolver: IEntityResolver,
        filter_extractor: IFilterExtractor,
        clarification_detector: IClarificationDetector,
        strategy_selector: IStrategySelector,
        budget_estimator: BudgetEstimator,
        assembler: PlanAssembler,
    ) -> None: ...

    def plan(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> RetrievalPlan: ...
```

`plan()` executes stages in order, collecting outputs and passing them forward:

1. `intent_classifier.classify(parse_result, config)` → `QueryIntent`
2. `entity_resolver.resolve(parse_result, config)` → `list[ResolvedEntity]`
3. `filter_extractor.extract(parse_result, config)` → `list[QueryFilter]`
4. `clarification_detector.detect(parse_result, intent, config)` → `(bool, str | None)`
5. `strategy_selector.select(intent, entities, filters, config)` → `list[StrategyType]`
   (skipped when `clarification_required=True`; returns `[]`)
6. `budget_estimator.estimate(intent, config)` → `RetrievalLimits`
7. `assembler.assemble(...)` → `RetrievalPlan`

The pipeline maintains **no instance state** between calls. All intermediate values are
local to the `plan()` invocation (NFR-004).

---

## 14. RetrievalPlannerRegistry

**File**: `src/core/retrieval_planner/registry.py`

Registry mapping strategy ids to implementation instances. Follows the same pattern
as `src/core/knowledge/registry.py`.

```python
class RetrievalPlannerRegistry:
    def register_intent_classifier(self, impl: IIntentClassifier) -> None: ...
    def register_entity_resolver(self, impl: IEntityResolver) -> None: ...
    def register_filter_extractor(self, impl: IFilterExtractor) -> None: ...
    def register_strategy_selector(self, impl: IStrategySelector) -> None: ...
    def register_clarification_detector(self, impl: IClarificationDetector) -> None: ...

    def build_pipeline(self, config: RetrievalPlannerConfig) -> RetrievalPlannerPipeline: ...
```

`build_pipeline` resolves each strategy id from `config` to the registered implementation
and constructs a `RetrievalPlannerPipeline`. Raises `StrategyNotFoundError` on unknown
strategy ids.

---

## 15. Default Implementations Summary

| Interface | Default ID | Class | File |
|---|---|---|---|
| `IIntentClassifier` | `"rule_based"` | `RuleBasedIntentClassifier` | `intent/rule_based.py` |
| `IEntityResolver` | `"query_plan"` | `QueryPlanEntityResolver` | `entities/query_plan_resolver.py` |
| `IFilterExtractor` | `"query_plan"` | `QueryPlanFilterExtractor` | `filters/query_plan_extractor.py` |
| `IStrategySelector` | `"config_driven"` | `ConfigDrivenStrategySelector` | `strategies/config_driven.py` |
| `IClarificationDetector` | `"confidence_based"` | `ConfidenceBasedClarificationDetector` | `clarification/confidence_based.py` |
| `BudgetEstimator` | *(internal)* | `BudgetEstimator` | `limits/budget_estimator.py` |
| `PlanAssembler` | *(internal)* | `PlanAssembler` | `assembly.py` |

---

## Entity Relationship Summary

```
  ParseResult (from spec 004)
    canonical_query
    query_plan.operation, .entities, .filters, .language, .confidence
          │
          ▼
  IIntentClassifier.classify()
          │
          ▼
  QueryIntent (category, confidence, secondary_categories, evidence)
          │
  IEntityResolver.resolve()
          │
          ▼
  list[ResolvedEntity] (entity_id, raw_text, canonical_form, entity_type)
          │
  IFilterExtractor.extract()
          │
          ▼
  list[QueryFilter] (filter_id, filter_type, field_name, operator, value, source)
          │
  IClarificationDetector.detect()
          │
    ┌─────┴─────────────────────┐
    │ clarification_required     │ clarification_required
    │  = True                    │  = False
    │                            ▼
    │             IStrategySelector.select()
    │                            │
    │                            ▼
    │             list[StrategyType] (ordered)
    │
  BudgetEstimator.estimate()
    │
    ▼
  RetrievalLimits (max_evidence_units, max_candidates, scope)
    │
  PlanAssembler.assemble()
    │
    ▼
  RetrievalPlan (immutable, frozen)
  ├── intent: QueryIntent
  ├── entities: tuple[ResolvedEntity, ...]
  ├── filters: tuple[QueryFilter, ...]
  ├── retrieval_strategies: tuple[StrategyType, ...]  ← empty if clarification_required
  ├── retrieval_limits: RetrievalLimits
  ├── retrieval_constraints: RetrievalConstraints
  ├── execution_hints: ExecutionHints | None
  ├── output_shape: OutputShape
  ├── clarification_required: bool
  ├── clarification_question: str | None
  ├── planner_confidence: float
  ├── diagnostics: PlannerDiagnostics | None
  └── metadata: RetrievalPlanMetadata
          │
          ▼
  Retrieval Engine V2 (spec 010)     ← consumes RetrievalPlan
  Evidence Orchestrator (spec 011)   ← consumes RetrievalPlan
  Context Builder (spec 012)         ← consumes output_shape, constraints
  Answer Generator (spec 013)        ← consumes output_shape, citation_required
```

---

## Module File Map

| File | Contents |
|---|---|
| `src/core/retrieval_planner/models.py` | `StrategyType`, `IntentCategory`, `OutputShapeType`, `QueryIntent`, `ResolvedEntity`, `QueryFilter`, `RetrievalLimits`, `RetrievalConstraints`, `ExecutionHints`, `OutputShape`, `PlannerDiagnostics`, `RetrievalPlanMetadata`, `RetrievalPlan`, `RetrievalPlannerConfig` |
| `src/core/retrieval_planner/interfaces.py` | `IRetrievalPlanner`, `IIntentClassifier`, `IEntityResolver`, `IFilterExtractor`, `IStrategySelector`, `IClarificationDetector` |
| `src/core/retrieval_planner/pipeline.py` | `RetrievalPlannerPipeline` |
| `src/core/retrieval_planner/assembly.py` | `PlanAssembler`, `ConstraintsBuilder`, `HintsBuilder`, `OutputShapeDeriver` |
| `src/core/retrieval_planner/registry.py` | `RetrievalPlannerRegistry` |
| `src/core/retrieval_planner/errors.py` | `RetrievalPlannerError`, `PlannerConfigError`, `StrategyNotFoundError`, `PlanAssemblyError` |
| `src/core/retrieval_planner/intent/rule_based.py` | `RuleBasedIntentClassifier` |
| `src/core/retrieval_planner/entities/query_plan_resolver.py` | `QueryPlanEntityResolver` |
| `src/core/retrieval_planner/filters/query_plan_extractor.py` | `QueryPlanFilterExtractor` |
| `src/core/retrieval_planner/strategies/config_driven.py` | `ConfigDrivenStrategySelector` |
| `src/core/retrieval_planner/clarification/confidence_based.py` | `ConfidenceBasedClarificationDetector` |
| `src/core/retrieval_planner/limits/budget_estimator.py` | `BudgetEstimator` |
| `src/fields/generic/retrieval_planning.yaml` | Generic field pack for planner config |
