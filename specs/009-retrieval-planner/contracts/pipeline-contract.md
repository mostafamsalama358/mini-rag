# Pipeline Contract: RetrievalPlan

**Feature**: `009-retrieval-planner` | **Date**: 2026-07-14
**Schema Version**: `1.0.0` | **Status**: Stable

This document is the **authoritative, stable public contract** for `RetrievalPlan` — the
interface between the Retrieval Planner (spec 009) and all downstream pipeline components.

Downstream specs MUST treat this document as the single source of truth for the contract
they consume. Any change to this document that increments the MAJOR schema version
requires explicit migration documentation and review by all downstream maintainers.

---

## Contract Stability Guarantee

| Scenario | Schema version change |
|---|---|
| Field removed or renamed on any published model | MAJOR increment required |
| Field type narrowed (e.g., `str \| None` → `str`) | MAJOR increment required |
| New **optional** field added | MINOR increment only |
| Validation rule tightened without shape change | PATCH increment only |
| Documentation or comment change only | PATCH increment only |

Downstream specs (010–013) MUST check `metadata.schema_version` major component. If
`major > expected_major`, the engine MUST reject the plan with a descriptive error (SC-011).

Additive optional fields (MINOR increments) MUST be handled gracefully by all existing
consumers — unknown optional fields are ignored.

---

## Upstream Producer

| Component | Spec | Output |
|---|---|---|
| Query Analysis | spec 004 | `ParseResult` (consumed by Planner as input) |
| Retrieval Planner | **spec 009** | `RetrievalPlan` (this contract) |

---

## Downstream Consumers

| Component | Spec | Fields consumed |
|---|---|---|
| Retrieval Engine V2 | spec 010 | `retrieval_strategies`, `retrieval_limits`, `retrieval_constraints`, `filters`, `entities`, `execution_hints`, `clarification_required`, `metadata.schema_version` |
| Evidence Orchestrator | spec 011 | `retrieval_limits.max_evidence_units`, `retrieval_constraints`, `entities`, `output_shape` |
| Context Builder | spec 012 | `output_shape`, `retrieval_constraints.citation_required`, `retrieval_constraints.required_language` |
| Answer Generator | spec 013 | `output_shape`, `retrieval_constraints.citation_required`, `intent.category` |

---

## RetrievalPlan Schema v1.0.0

### Top-Level Fields

```
RetrievalPlan
├── intent:                 QueryIntent          (required)
├── entities:               tuple[ResolvedEntity, ...]  (required; empty tuple if none)
├── filters:                tuple[QueryFilter, ...]     (required; always includes language filter)
├── retrieval_strategies:   tuple[StrategyType, ...]    (required; empty iff clarification_required)
├── retrieval_limits:       RetrievalLimits      (required)
├── retrieval_constraints:  RetrievalConstraints (required)
├── execution_hints:        ExecutionHints | None (optional; None if no hints)
├── output_shape:           OutputShape          (required)
├── clarification_required: bool                 (required)
├── clarification_question: str | None           (required when clarification_required=True)
├── planner_confidence:     float [0.0, 1.0]     (required)
├── diagnostics:            PlannerDiagnostics | None  (optional; None in production)
└── metadata:               RetrievalPlanMetadata (required)
```

---

### QueryIntent

```
QueryIntent
├── category:              IntentCategory       (required)
├── confidence:            float [0.0, 1.0]     (required)
├── secondary_categories:  tuple[IntentCategory, ...] (required; empty tuple if none)
└── evidence:              tuple[str, ...]      (required; phrases driving classification)
```

`IntentCategory` values: `factual | list | comparative | procedural | tabular | navigational | mixed`

---

### ResolvedEntity

```
ResolvedEntity
├── entity_id:      str   ("ent_" + SHA256 prefix; required)
├── raw_text:       str   (required; non-empty)
├── canonical_form: str   (required; non-empty)
├── entity_type:    str   (required; open extensible type)
└── source_span:    tuple[int, int] | None  (optional; char offsets in canonical_query)
```

---

### QueryFilter

```
QueryFilter
├── filter_id:   str   ("flt_" + SHA256 prefix; required)
├── filter_type: str   (required; open: "date", "language", "category", "document_type", etc.)
├── field_name:  str   (required; non-empty logical field name)
├── operator:    str   (required; one of: eq, neq, lt, gt, lte, gte, in, not_in, contains, range)
├── value:       Any   (required)
└── source:      "explicit" | "implicit"  (required)
```

---

### RetrievalLimits

```
RetrievalLimits
├── max_evidence_units: int  (required; >= 1; max units engine may return)
├── max_candidates:     int  (required; >= max_evidence_units; max candidates before selection)
└── scope:              "narrow" | "standard" | "broad" | "exhaustive"  (required)
```

**Engine note**: `max_candidates` is an advisory budget for candidate consideration before
downstream ranking or selection. It does not prescribe any specific algorithm. The engine
may use it to bound resource usage without being constrained to a particular implementation.

---

### RetrievalConstraints

```
RetrievalConstraints
├── latency_budget_ms:  int | None    (optional; engine wall time cap in ms)
├── cost_budget:        float | None  (optional; abstract cost budget)
├── freshness_window:   str | None    (optional; ISO 8601 duration, e.g. "P30D")
├── required_language:  str | None    (optional; ISO 639-1, e.g. "en", "ar")
└── citation_required:  bool          (required; True = engine must return source citations)
```

**Engine obligation**: When `citation_required=True`, every returned evidence unit MUST
include traceable source metadata (document id, chunk id, excerpt). This requirement flows
from Constitution VI.4 and MUST NOT be suppressed by the engine.

---

### ExecutionHints

```
ExecutionHints                        (entire field is None if no hints triggered)
├── preferred_document_types:  list[str] | None  (advisory)
├── preferred_section_kinds:   list[str] | None  (advisory)
├── expand_entities:           bool | None       (advisory)
├── allow_table_search:        bool | None       (advisory)
└── prioritize_recent_content: bool | None       (advisory)
```

**Engine obligation**: All hints are **safely ignorable**. Ignoring any or all hints MUST
NOT change retrieval correctness — only optional optimizations. Engines MUST NOT raise
errors for unrecognized hint fields (forward compatibility for MINOR additions).

---

### OutputShape

```
OutputShape
├── shape_type: "single_fact" | "list" | "summary" | "table" | "comparison" | "narrative"
├── max_items:  int | None  (optional; for list/table shapes)
└── structured: bool        (True = machine-parseable; False = free-text)
```

---

### PlannerDiagnostics (internal, not a consumer contract)

```
PlannerDiagnostics                    (None in production; present when diagnostics_enabled)
├── intent_candidates:         list[dict]
├── entity_resolution_trace:   list[dict]
├── strategy_selection_trace:  list[dict]
├── clarification_trigger:     str | None
├── limits_derivation:         dict
└── planning_latency_ms:       float
```

Downstream specs MUST NOT depend on `PlannerDiagnostics` fields. This sub-object may be
`None` in any deployment. Its internal structure may change without a schema version
increment.

---

### RetrievalPlanMetadata

```
RetrievalPlanMetadata
├── plan_id:        str  ("rp_" + SHA256 prefix; deterministic; required)
├── planner_version: str  (semantic version of Planner implementation)
├── schema_version:  str  (semantic version of this contract; check major before consuming)
├── config_hash:    str  (8-char config fingerprint)
└── created_at:     str  (ISO 8601 UTC)
```

---

### StrategyType Vocabulary

`StrategyType` is an open, non-exhaustive string type. Available values are configured
per domain in the field pack YAML. The initial vocabulary:

| Value | Semantics |
|---|---|
| `semantic` | Dense/semantic similarity retrieval |
| `keyword` | Sparse/keyword-based retrieval |
| `metadata` | Filter-driven retrieval by document metadata |
| `graph` | Graph-traversal retrieval over knowledge relationships |
| `document` | Full-document retrieval |
| `section` | Section-scoped retrieval |
| `table` | Tabular content retrieval |
| `hybrid` | Combined dense + sparse retrieval |
| `mixed` | Multi-strategy retrieval selected by the engine |

Engines MUST handle strategy types they do not implement by skipping them (not by
raising an error). If all listed strategies are unsupported, the engine should use its
default strategy and log a warning.

---

## Invariants

These invariants hold for every valid `RetrievalPlan` regardless of schema version:

1. **Clarification gate**: When `clarification_required=True`, `retrieval_strategies` is
   empty. Retrieval MUST NOT begin.
2. **Non-empty strategies**: When `clarification_required=False`, `retrieval_strategies`
   contains at least one element.
3. **Citation propagation**: `retrieval_constraints.citation_required` is always present
   (never `None`). Default value is `True`.
4. **Determinism**: Identical `canonical_query` + identical `config_hash` always produce
   a plan with the same `metadata.plan_id`.
5. **Engine-agnostic content**: `RetrievalPlan` contains no SQL, vector index identifiers,
   BM25 expressions, embedding configurations, or other retrieval-engine-specific artifacts.
6. **Immutability**: Once returned by the Planner, the plan object is frozen — no field
   may be mutated. Downstream components MUST treat it as read-only.

---

## Forward Compatibility

New optional fields may be added to any model at any MINOR schema version. Consumers MUST:

- Ignore unknown fields at the top level and within sub-objects.
- Not fail on `None` values for fields that were previously required (field may have been
  made optional in a MINOR version).
- Check `metadata.schema_version` MAJOR component before processing.

---

## Versioning History

| Version | Date | Change |
|---|---|---|
| `1.0.0` | 2026-07-14 | Initial stable contract |
