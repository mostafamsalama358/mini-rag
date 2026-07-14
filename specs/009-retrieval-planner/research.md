# Research: Retrieval Planner

**Feature**: `009-retrieval-planner` | **Date**: 2026-07-14

This document resolves all unknowns identified in the Technical Context during Phase 0.
Every decision is incorporated into the Phase 1 design artifacts (data-model.md,
contracts/, quickstart.md).

---

## R1 — Planner Input: Relationship with Existing QueryPlan (spec 004)

**Decision**: The Retrieval Planner receives a `ParseResult` from the query parser
(spec 004, `src/core/query_parser/schema.py`) as its primary input. The `ParseResult`
carries: `original_query`, `canonical_query`, `query_plan` (`QueryPlan` with `operation`,
`scope`, `field`, `entities`, `language`, `filters`, `confidence`, `needs_clarification`,
`clarification_prompt`), `used_llm`, `latency_ms`.

The Planner **does not replace** the existing `QueryPlan`. It enriches and formalizes
it into a `RetrievalPlan`. The two contracts serve different purposes:

| Contract | Owner | Purpose |
|---|---|---|
| `QueryPlan` (spec 004) | Query Parser | Structured parse of a query: operation type, field, scope, basic entities and filters |
| `RetrievalPlan` (spec 009) | Retrieval Planner | Full execution contract: ordered strategies, limits, constraints, hints, clarification gate, confidence, diagnostics |

**Rationale**: Reusing the existing `ParseResult` avoids duplicating query parsing logic.
The Planner's role is to translate a parsed query into a retrieval contract, not to
re-parse it. This keeps spec 004 and spec 009 independently evolvable.

**Alternative considered — Planner receives raw query string**: Would require the Planner
to embed query parsing logic; rejected as it violates single responsibility and couples
the Planner to a parsing implementation.

**Alternative considered — Planner replaces QueryPlan entirely**: Would break spec 004
consumers (existing RAG service, interaction retrieval); rejected for backward
compatibility.

---

## R2 — StrategyType: Open Extensible Type vs Closed Literal

**Decision**: `StrategyType` is defined as `Annotated[str, Field(min_length=1)]` — an
open, non-exhaustive string-backed type. Available strategies for a domain are declared
in the field pack YAML under `retrieval_planning.available_strategies`. The planner
validates selected strategies against the configured available set at plan time; an
unrecognized strategy in the output triggers a `PlannerConfigError`.

Initial vocabulary (FR-014): `semantic`, `keyword`, `metadata`, `graph`, `document`,
`section`, `table`, `hybrid`, `mixed`.

New strategy types are added by:
1. Registering the name in the relevant field pack YAML (zero code change to Planner).
2. Implementing the execution in Retrieval Engine V2 (spec 010) — entirely separate.

**Rationale**: A closed `Literal` enum would require a Planner code change every time
the Retrieval Engine V2 adds a new backend strategy. An open string type with a
field-pack-driven vocabulary registry satisfies FR-014 (extensible without architecture
change) and SC-010 (new type via YAML only).

**Alternative considered — `Enum` subclass**: Closed by default in Python; requires code
change to add values; rejected (FR-014).

**Alternative considered — `Protocol`-based registry**: Overengineering for a vocabulary
list; rejected.

---

## R3 — Immutability Enforcement

**Decision**: Use Pydantic v2 `ConfigDict(frozen=True)` on all published models:
`RetrievalPlan`, `QueryIntent`, `ResolvedEntity`, `QueryFilter`, `RetrievalLimits`,
`RetrievalConstraints`, `ExecutionHints`, `OutputShape`, `RetrievalPlanMetadata`.

`PlannerDiagnostics` uses `frozen=False` — it is an internal mutable assembly artifact
that is optionally included in the final plan.

**Rationale**: Identical pattern to `008-knowledge-representation` (`KnowledgePackage`,
`KnowledgeUnit`). Frozen Pydantic models enforce immutability at the Python object level
without copy-on-write complexity.

---

## R4 — RetrievalPlan ID Scheme

**Decision**: `plan_id = "rp_" + SHA256(canonical_payload)[:16]` where
`canonical_payload = f"{canonical_query}|{intent.category}|{'|'.join(sorted(retrieval_strategies))}|{config_hash}"`.

This ensures: same query + same config → same `plan_id` (determinism, NFR-003); different
queries always differ (collision probability negligible at 64-bit prefix).

**Rationale**: Consistent with `007` (`ck_` prefix) and `008` (`ku_`, `kr_`, `kp_`
prefixes). Deterministic IDs support idempotent downstream caching.

**Alternative considered — UUID4**: Non-deterministic; breaks idempotency; rejected.

---

## R5 — Intent Classification: Mapping QueryPlan.operation → IntentCategory

**Decision**: `RuleBasedIntentClassifier` maps the upstream `QueryPlan` to an
`IntentCategory` using a two-pass rule table:

**Pass 1 — Upstream operation mapping** (deterministic):

| `QueryPlan.operation` | Primary `IntentCategory` |
|---|---|
| `lookup` | `factual` |
| `list` | `list` |
| `compare` | `comparative` |
| `explain` | `procedural` |
| `count` | `factual` |
| `unsupported` | → pass 2 (text patterns) |

**Pass 2 — Text pattern augmentation** (applied over canonical_query for all operations):

| Pattern | Overrides to |
|---|---|
| `\b(table|tabular|row|column|schedule)\b` (case-insensitive) | `tabular` |
| `\b(how to|steps|procedure|process)\b` | `procedural` (if not already comparative) |
| `\b(compare|versus|vs\.?|difference between)\b` | `comparative` |
| `\b(navigate|find|where is|location of)\b` | `navigational` |
| Multiple distinct operation signals present | `mixed` |

`confidence` is set to `1.0` for Pass 1 exact matches, `0.8` for Pass 2 pattern-driven
overrides, `0.6` for `unsupported` operations that match a Pass 2 pattern, and `0.4`
for `unsupported` with no pattern match.

**Rationale**: Leveraging the existing `QueryPlan.operation` ensures consistency with
the upstream parse. Text patterns catch cases the parser did not classify
(e.g., tabular intent in a `lookup` operation). The two-pass design is stateless and
deterministic.

**Alternative considered — LLM-based classification**: Non-deterministic, adds latency;
rejected as default (NFR-003, SC-002).

---

## R6 — Entity Resolution Strategy

**Decision**: `QueryPlanEntityResolver` wraps `ParseResult.query_plan.entities` (a
`list[str]` of raw entity strings) into `ResolvedEntity` objects. Canonical form
resolution uses an alias lookup table loaded from the field pack YAML
(`retrieval_planning.entity_aliases`). If no alias match, canonical_form = raw text.
`entity_type` is assigned via a keyword-pattern table in the field pack YAML
(`retrieval_planning.entity_type_patterns`).

Each `ResolvedEntity.entity_id = "ent_" + SHA256(f"{canonical_form}|{entity_type}")[:16]`.

**Rationale**: Entities are already extracted by the query parser. The resolver only
adds typing and canonicalization — no NLP needed. Alias tables in field pack YAML allow
domain-specific entity resolution without Planner code changes.

**Alternative considered — NLP-based NER**: Adds latency and non-determinism; reserved
for an optional alternative implementation behind `IEntityResolver`.

---

## R7 — Filter Extraction Strategy

**Decision**: `QueryPlanFilterExtractor` wraps `ParseResult.query_plan.filters`
(`dict[str, Any]`) into `QueryFilter` objects. Each key-value pair in the dict becomes
one `QueryFilter`. The filter `source` field is set to `"explicit"` for filters
originating from the parsed query and `"implicit"` for filters inferred from language
or field context (e.g., language filter from `query_plan.language`).

A `language` filter is always added implicitly when `query_plan.language` is non-empty,
using `filter_type="language"`, `operator="eq"`, `value=language`.

**Rationale**: Directly wraps existing filter data; no new extraction logic required.
The implicit language filter ensures downstream retrieval respects the detected query
language without requiring the engine to re-detect it.

---

## R8 — Strategy Selection: intent → ordered strategies

**Decision**: `ConfigDrivenStrategySelector` reads a strategy mapping table from the
field pack YAML (`retrieval_planning.strategy_mappings`) and returns an ordered list of
`StrategyType` values for the classified `IntentCategory`. The ordering expresses
Planner preference; the Retrieval Engine MAY reorder at runtime (FR-005, spec revision).

**Default mapping (generic field pack)**:

| `IntentCategory` | Primary | Secondary | Tertiary |
|---|---|---|---|
| `factual` | `semantic` | `hybrid` | — |
| `list` | `semantic` | `keyword` | — |
| `comparative` | `semantic` | `hybrid` | `graph` |
| `procedural` | `semantic` | `document` | — |
| `tabular` | `table` | `semantic` | — |
| `navigational` | `metadata` | `document` | — |
| `mixed` | `hybrid` | `semantic` | `keyword` |

If a listed strategy is not in `available_strategies` for the active field pack, it is
silently omitted. A minimum of one strategy must remain; if all are excluded, the fallback
is the configured `default_strategy` (default: `"semantic"`).

**Rationale**: Table-driven selection makes domain customization zero-code (SC-010). The
Retrieval Engine is free to reorder for runtime reasons while preserving intent (FR-005).

---

## R9 — Clarification Detection Logic

**Decision**: `ConfidenceBasedClarificationDetector` triggers clarification when any of
three conditions is met (evaluated in priority order):

1. **Upstream clarification**: `ParseResult.query_plan.needs_clarification == True` →
   propagate upstream `clarification_prompt` as the `clarification_question`.
2. **Low intent confidence**: `QueryIntent.confidence < config.clarification_confidence_threshold`
   (default `0.5` in generic field pack) → generate a clarification question from the
   secondary intent candidates.
3. **Empty query**: `canonical_query` is empty or whitespace-only → clarification required.

`planner_confidence` is set to `min(QueryIntent.confidence, ParseResult.query_plan.confidence or 1.0)`.

**Rationale**: Condition 1 preserves upstream clarification decisions. Condition 2 catches
cases where the Planner's intent classification is uncertain. Condition 3 is a defensive
guard. The threshold is configurable per domain (legal domains may require higher confidence
before executing expensive retrieval).

---

## R10 — RetrievalLimits Derivation

**Decision**: `BudgetEstimator` derives `RetrievalLimits` from the active field pack
configuration and the classified `IntentCategory`:

| `IntentCategory` | `scope` | `max_evidence_units` (default) | `max_candidates` (default) |
|---|---|---|---|
| `factual` | `narrow` | 5 | 20 |
| `list` | `standard` | 10 | 40 |
| `comparative` | `standard` | 8 | 30 |
| `procedural` | `standard` | 8 | 30 |
| `tabular` | `narrow` | 3 | 10 |
| `navigational` | `narrow` | 3 | 15 |
| `mixed` | `broad` | 15 | 60 |

All values are overridable per domain in field pack YAML
(`retrieval_planning.budget_defaults`). The field pack ceiling (if set) caps these values.

**Rationale**: Different intent types have different evidence volume requirements. Factual
queries need fewer but more precise units; list queries need more. `max_candidates` gives
the engine a guidance budget for candidate consideration before ranking/selection —
implementation-agnostic as required (spec revision item 1).

---

## R11 — PlannerDiagnostics Toggle

**Decision**: `PlannerDiagnostics` is an optional field on `RetrievalPlan`
(`diagnostics: PlannerDiagnostics | None`). A `diagnostics_enabled: bool` field in
`RetrievalPlannerConfig` controls whether it is populated (default: `False` in
production, `True` in testing). When disabled, the field is `None` and no diagnostic
computation overhead is incurred.

**Rationale**: Diagnostics are internal metadata useful for debugging strategy selection
and intent classification. They must not appear in user-visible responses or affect
retrieval correctness. Toggling them off in production reduces payload size (spec
revision item 5, assumption in spec.md).

---

## R12 — Constraints Population

**Decision**: `RetrievalConstraints` is populated by a dedicated `ConstraintsBuilder`
(internal to `PlanAssembler`) using:

- `latency_budget_ms`: from field pack `retrieval_planning.default_latency_budget_ms`;
  `None` if unset.
- `cost_budget`: from field pack `retrieval_planning.default_cost_budget`; `None` if unset.
- `freshness_window`: extracted from query filters (if a date/recency filter is present)
  or from field pack defaults; `None` if absent.
- `required_language`: from `QueryPlanFilterExtractor`'s implicit language filter.
- `citation_required`: from field pack `retrieval_planning.citation_required` (default:
  `True`, aligned with Constitution VI.4 source citations mandate).

All fields are optional; `None` signals "no constraint" to the engine.

---

## R13 — ExecutionHints Population

**Decision**: `ExecutionHints` is populated by a dedicated `HintsBuilder` (internal to
`PlanAssembler`) using intent + entity signals:

| Condition | Hint set |
|---|---|
| `intent.category == "tabular"` | `allow_table_search = True` |
| entities resolved with `entity_type == "document"` | `preferred_document_types = [entity.canonical_form for ...]` |
| entities resolved with `entity_type == "section"` | `preferred_section_kinds = [...]` |
| `intent.category` in `{"comparative", "mixed"}` | `expand_entities = True` |
| `retrieval_constraints.freshness_window` is set | `prioritize_recent_content = True` |

If no hints are generated (all fields remain `None`), `execution_hints` is `None` on
the plan (lean default).

---

## R14 — Forward Compatibility and Schema Versioning

**Decision**: `RetrievalPlanMetadata.schema_version` is initialized to `"1.0.0"`.
Version semantics:
- **MAJOR** increment: any field removed, renamed, or type-narrowed on `RetrievalPlan`
  or any required sub-model.
- **MINOR** increment: new optional field added to any published model.
- **PATCH** increment: documentation or validation rule changes with no model shape change.

Retrieval Engine V2 (spec 010) MUST check `schema_version` major component at startup.
If `major > expected_major`, the engine MUST reject the plan with a descriptive error
(SC-011).

**Rationale**: Explicit versioning satisfies SC-007 and SC-011. Major version checks at
the engine boundary prevent silent misinterpretation of plans from future Planner
versions.

---

## Summary of All Decisions

| Decision | Choice | Gate |
|---|---|---|
| Planner input | `ParseResult` from spec 004; Planner enriches, does not replace | FR-001 |
| `StrategyType` | Open `Annotated[str, Field(min_length=1)]`; vocabulary in field pack YAML | FR-014, SC-010 |
| Immutability | Pydantic v2 `frozen=True` on all published models | NFR-003 |
| Plan ID scheme | `"rp_" + SHA256(canonical_query|intent|sorted_strategies|config_hash)[:16]` | NFR-003 |
| Intent classification | `RuleBasedIntentClassifier`: operation mapping + text patterns | FR-002, NFR-003 |
| Entity resolution | `QueryPlanEntityResolver`: wraps upstream entities + alias/type lookup | FR-003 |
| Filter extraction | `QueryPlanFilterExtractor`: wraps upstream filters + implicit language | FR-004 |
| Strategy selection | `ConfigDrivenStrategySelector`: table-driven from field pack YAML | FR-005, SC-010 |
| Clarification detection | `ConfidenceBasedClarificationDetector`: upstream flag + confidence threshold + empty check | FR-009, FR-010 |
| Retrieval limits | `BudgetEstimator`: intent→defaults table + field pack ceiling | FR-006 |
| Constraints | `ConstraintsBuilder`: field pack defaults + filter signals | FR-007 |
| Execution hints | `HintsBuilder`: intent + entity signals; `None` if no hints triggered | FR-018 |
| Diagnostics toggle | Optional field; `diagnostics_enabled` in config; default `False` in prod | FR-012, NFR-011 |
| Schema versioning | Semantic versioning on `schema_version`; major check at engine startup | SC-007, SC-011 |
