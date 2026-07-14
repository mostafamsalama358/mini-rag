# Feature Specification: Retrieval Planner

**Feature Branch**: `009-retrieval-planner`

**Created**: 2026-07-14

**Status**: Draft

## Architecture Overview

The Retrieval Planner occupies a single, bounded position in the pipeline:

```
User Query
    ↓
Query Analysis
    ↓
Retrieval Planner          ← this spec
    ↓
RetrievalPlan              ← stable public contract
    ↓
Retrieval Engine V2        ← spec 010
    ↓
Evidence Orchestrator      ← spec 011
    ↓
Context Builder            ← spec 012
    ↓
Answer Generator           ← spec 013
```

**Responsibility boundary**:

| Component | Responsibility |
|---|---|
| Retrieval Planner | Decides *what* to retrieve and *under what constraints* |
| Retrieval Engine V2 | Decides *how* to retrieve; translates plan into index operations |
| Evidence Orchestrator | Organizes retrieved evidence into coherent evidence sets |
| Context Builder | Constructs LLM context from organized evidence |
| Answer Generator | Produces the final answer |

The Planner MUST NOT perform any responsibility listed for a downstream component.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Deterministic Plan from Unambiguous Query (Priority: P1)

A developer passes a clear, well-formed natural-language query to the Retrieval Planner.
The Planner analyzes the query, classifies intent, resolves entities, selects ordered
retrieval strategies, and returns a fully populated `RetrievalPlan` — without touching
any retrieval infrastructure.

**Why this priority**: This is the core deliverable. Every downstream spec (010–013)
depends on receiving a correctly formed `RetrievalPlan`. Without this, the separation
of planning from execution cannot be validated.

**Independent Test**: Can be fully tested by submitting a clear query (e.g.,
"What are the contraindications for ibuprofen?") to the planner interface and asserting
that the returned `RetrievalPlan` contains correct intent, ordered strategies, retrieval
limits, constraints, and zero evidence of retrieval being executed.

**Acceptance Scenarios**:

1. **Given** a clear natural-language query, **When** the Planner processes it, **Then** a `RetrievalPlan` is returned with `clarification_required = false`, a non-empty ordered `retrieval_strategies` list, a non-empty intent, and populated entity and filter fields.
2. **Given** the same query submitted twice with no configuration change, **When** both plans are compared, **Then** the outputs are identical (determinism guarantee).
3. **Given** any query, **When** the Planner runs, **Then** no retrieval index, vector store, graph store, or database is queried.

---

### User Story 2 — Ambiguous Query Triggers Clarification (Priority: P2)

A developer submits a query that the Planner cannot resolve to a single unambiguous
intent. The Planner sets `clarification_required = true`, provides a `clarification_question`,
and returns without producing a plan body that could trigger execution.

**Why this priority**: Prevents downstream engines from acting on under-specified plans,
which would degrade answer quality and waste retrieval resources.

**Independent Test**: Can be fully tested by submitting an intentionally vague query
(e.g., "Tell me about it") and asserting that `clarification_required = true` and a
non-empty `clarification_question` is returned.

**Acceptance Scenarios**:

1. **Given** a query with no discernible intent, **When** the Planner processes it, **Then** `clarification_required = true` and `clarification_question` is non-empty.
2. **Given** a query that resolves to two equally probable intents, **When** the Planner evaluates it, **Then** `clarification_required = true` and the question surfaces both candidate interpretations.
3. **Given** `clarification_required = true`, **When** the plan is returned, **Then** `retrieval_strategies` is empty and `retrieval_limits` signals that execution must not proceed.

---

### User Story 3 — Ordered Strategy Selection Based on Query Type (Priority: P2)

A developer submits different query types (fact lookup, document scan, tabular data
request, keyword search). For each type, the Planner selects an ordered list of
preferred retrieval strategies expressing Planner intent. The Retrieval Engine MAY
reorder execution based on runtime conditions (unavailable strategy, disabled capability,
resource constraints, latency budget, cost budget) while preserving that intent.

**Why this priority**: Strategy selection is the primary reasoning value the Planner
adds. Correct strategy ordering determines recall, precision, and retrieval cost.

**Independent Test**: Can be fully tested by submitting three queries of distinct types
and asserting that each resulting `RetrievalPlan` carries a different, contextually
correct ordered `retrieval_strategies` list.

**Acceptance Scenarios**:

1. **Given** a fact-lookup query, **When** the Planner runs, **Then** `retrieval_strategies` includes `semantic` or `hybrid` as the first-priority strategy.
2. **Given** a table-oriented query ("Show me dosage table for aspirin"), **When** the Planner runs, **Then** `retrieval_strategies` includes `table`.
3. **Given** a structured keyword query, **When** the Planner runs, **Then** `retrieval_strategies` lists `keyword` or `metadata` at highest priority.
4. **Given** a complex multi-intent query, **When** the Planner runs, **Then** `retrieval_strategies` contains more than one strategy in priority order.

---

### User Story 4 — Domain-Agnostic Configuration (Priority: P3)

An operator configures the Planner via a YAML field pack (generic, legal, pharmacy)
and switches domains without modifying Planner source code. The Planner respects
configuration-driven strategy availability, retrieval limits, constraints, and
confidence thresholds.

**Why this priority**: Domain agnosticism is a non-negotiable architectural property
inherited from specs 002 and 006–008.

**Independent Test**: Can be fully tested by loading the generic field pack, then the
pharmacy pack, and asserting that available strategies and evidence limits differ
between runs without any code change.

**Acceptance Scenarios**:

1. **Given** a generic field pack, **When** the Planner processes a query, **Then** no domain-specific logic influences plan outputs.
2. **Given** a domain field pack that excludes `graph` strategy, **When** any query is processed, **Then** `retrieval_strategies` never contains `graph`.
3. **Given** a field pack specifying a maximum evidence budget, **When** the Planner returns a plan, **Then** `retrieval_limits.max_evidence_units` does not exceed that ceiling.

---

### Edge Cases

- What happens when the query is empty or whitespace-only? — Planner returns a plan with `clarification_required = true`, empty `retrieval_strategies`, and a prompt to provide a valid query.
- What happens when no configured strategy matches the classified intent? — Planner falls back to the configured default strategy, lowers `planner_confidence`, and records the fallback in `planner_diagnostics`.
- What happens when entity resolution produces zero entities? — Plan is still valid; entities list is empty; strategy selection proceeds on intent alone.
- What happens when the configured field pack is missing or malformed? — Planner raises a configuration error before attempting planning; no partial plan is returned.
- What happens when two strategies are equally applicable? — Planner orders them by configured priority and records both candidates in `planner_diagnostics`.
- What happens when a constraint cannot be expressed without referencing a specific retrieval technology? — The constraint is expressed generically (e.g., `freshness: 30d`) and translation into technology-specific form is left to the Retrieval Engine.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Planner MUST accept a natural-language query and produce a `RetrievalPlan` as its sole output.
- **FR-002**: The Planner MUST classify query intent (e.g., factual, comparative, navigational, procedural, tabular).
- **FR-003**: The Planner MUST extract named entities referenced in the query and attach them to the plan.
- **FR-004**: The Planner MUST extract explicit and implicit filters (date ranges, categories, document types, field values) from the query.
- **FR-005**: The Planner MUST select an ordered list of preferred retrieval strategies (`retrieval_strategies`) expressing Planner intent. The Retrieval Engine MAY reorder execution based on runtime conditions (unavailable strategy, disabled capability, resource constraints, latency budget, cost budget) while preserving Planner intent. The Planner owns intent; the Retrieval Engine owns execution decisions.
- **FR-006**: The Planner MUST populate `retrieval_limits` describing generic execution bounds (maximum evidence units, maximum candidates the engine may consider before downstream ranking or evidence selection, search breadth scope, and any configured ceilings) without referencing retrieval-algorithm internals.
- **FR-007**: The Planner MUST populate `retrieval_constraints` with generic execution constraints derived from the query and configuration. Supported constraint types include: `latency_budget`, `cost_budget`, `freshness`, `language`, and `citation_required`. Additional constraint types may be added via configuration without requiring Planner code changes.
- **FR-008**: The Planner MUST determine the expected output shape (e.g., single fact, list, summary, table).
- **FR-009**: The Planner MUST detect ambiguous queries and set `clarification_required = true` when intent cannot be resolved with sufficient confidence.
- **FR-010**: The Planner MUST provide a `clarification_question` whenever `clarification_required = true`.
- **FR-011**: The Planner MUST produce a `planner_confidence` score (normalized 0–1) reflecting certainty in the plan.
- **FR-012**: The Planner MUST populate `planner_diagnostics` with structured reasoning traces for debugging. Diagnostics are internal metadata only — they are not part of user-visible outputs and MAY be omitted in production deployments where performance or payload size requires it.
- **FR-013**: The `RetrievalPlan` MUST be a stable, versioned, immutable data contract. Specs 010–013 MUST be able to consume it without breaking changes to this contract. Breaking changes require a schema version increment. Backward-compatible additions (new optional fields) do not require a version increment.
- **FR-014**: The Planner MUST support an open, extensible `StrategyType` vocabulary. The initial vocabulary includes: `semantic`, `keyword`, `metadata`, `graph`, `document`, `section`, `table`, `hybrid`, `mixed`. New strategy types MUST be addable via configuration or extension without modifying Planner architecture.
- **FR-015**: The Planner MUST be configurable via field pack YAML (available strategies, retrieval limits, constraint defaults, confidence thresholds) using the mechanism from spec 002.
- **FR-016**: The Planner MUST perform zero retrieval operations — no vector search, no index lookup, no graph traversal, no database query of any kind.
- **FR-017**: The `RetrievalPlan` MUST NOT contain retrieval-engine-specific implementation details. Fields that MUST never appear include: SQL queries, vector index identifiers, BM25 expressions, graph traversal instructions, embedding provider configuration, or any other technology-specific artifact. The Planner expresses intent; the Retrieval Engine translates intent into implementation.
- **FR-018**: The Planner MAY populate optional `execution_hints` with engine-agnostic recommendations. Hints MUST be safely ignorable: ignoring any or all hints MUST NOT change the correctness of retrieval — only its optional optimizations. The Retrieval Engine is not required to honor any hint. Examples: preferred document types, preferred section kinds, `expand_entities`, `allow_table_search`, `prioritize_recent_content`. Hints MUST NOT reference specific retrieval technology.

### Key Entities

- **`RetrievalPlan`**: The immutable, versioned output contract of the Planner. Fields: `intent`, `entities`, `filters`, `retrieval_strategies`, `retrieval_limits`, `retrieval_constraints`, `execution_hints`, `output_shape`, `clarification_required`, `clarification_question`, `planner_confidence`, `planner_diagnostics`, `schema_version`.
- **`QueryIntent`**: Classified representation of what the user wants — includes intent category, confidence, and supporting evidence from query analysis.
- **`ResolvedEntity`**: A named entity extracted from the query, with type, canonical form, and source span.
- **`QueryFilter`**: A structured filter derived from the query — includes filter type (date, category, field), operator, and value.
- **`StrategyType`**: An open, extensible string-backed type representing a retrieval approach. Not a closed enumeration. New values are registered via field pack configuration without Planner code changes.
- **`RetrievalLimits`**: Generic execution bounds expressing *how much* the engine may retrieve — without referencing algorithm internals. Fields: `max_evidence_units` (maximum evidence units to return), `max_candidates` (maximum candidate items the engine may consider before downstream ranking or evidence selection), `scope` (search breadth: narrow / standard / broad / exhaustive). Additional limit fields may be added as optional extensions.
- **`RetrievalConstraints`**: Generic execution constraints the Retrieval Engine must respect. Fields are additive and optional. Initial set: `latency_budget_ms`, `cost_budget`, `freshness_window`, `required_language`, `citation_required`. The Planner declares constraints; the Retrieval Engine enforces them.
- **`ExecutionHints`**: Optional, engine-agnostic advisory recommendations. All hints MUST be safely ignorable: ignoring any or all hints MUST NOT change retrieval correctness — only optional optimizations. Fields: `preferred_document_types`, `preferred_section_kinds`, `expand_entities`, `allow_table_search`, `prioritize_recent_content`. All fields optional. The Retrieval Engine may ignore any or all hints without affecting plan validity.
- **`PlannerDiagnostics`**: Internal debugging metadata — strategy candidates considered, entity resolution trace, confidence breakdown. Not part of user-visible output. MAY be stripped in production deployments.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Planner MUST respect Clean Architecture layer boundaries — no retrieval infrastructure imports inside planner core.
- **NFR-002**: All planner I/O interfaces MUST be fully type-hinted; Pydantic models MUST back `RetrievalPlan` and all sub-entities.
- **NFR-003**: Planner MUST be deterministic — identical query input and identical configuration MUST always produce identical `RetrievalPlan` outputs.
- **NFR-004**: Planner MUST be stateless — planning outcome depends only on the input query, active configuration, and deterministic logic. The Planner MUST NOT maintain runtime state between requests, cache intermediate results across invocations, or rely on external mutable state.
- **NFR-005**: Planner MUST be domain-agnostic — no pharmacy, legal, or other domain-specific logic in core planner code.
- **NFR-006**: Planner MUST be configuration-driven via field pack YAML using the strategy selection/configuration mechanism from spec 002.
- **NFR-007**: Planner MUST be independently testable without any running retrieval infrastructure.
- **NFR-008**: Unit tests MUST cover: intent classification, entity resolution, filter extraction, strategy ordering, clarification detection, constraint population, execution hint generation, confidence scoring, and diagnostics output.
- **NFR-009**: Golden plan tests MUST cover a representative set of query types and assert full plan shape stability across schema versions.
- **NFR-010**: `RetrievalPlan` schema version MUST be incremented following semantic versioning on any breaking change to the contract. New optional fields are non-breaking and do not require a version increment.
- **NFR-011**: Structured logging MUST include `query_id`, `intent_category`, `strategies`, `confidence`, and `latency_ms` at the planner boundary.
- **NFR-012**: Secrets MUST NOT appear in planner configuration or logs.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unambiguous queries produce a fully populated `RetrievalPlan` with all required fields present and valid.
- **SC-002**: Planning latency for standard queries does not exceed 50 ms (excluding upstream query analysis preprocessing).
- **SC-003**: Identical queries under identical configuration produce identical `RetrievalPlan` outputs across 100 consecutive invocations (determinism).
- **SC-004**: At least 90% of golden test queries are assigned the expected primary strategy when evaluated against the golden plan suite.
- **SC-005**: Ambiguous query detection achieves at least 85% precision on a labeled ambiguity test set (no excessive false positives that block clear queries).
- **SC-006**: Zero retrieval-related imports or calls are present in the planner core module, verified by static analysis.
- **SC-007**: `RetrievalPlan` is a stable public contract. Retrieval Engine V2 (spec 010), Evidence Orchestrator (spec 011), Context Builder (spec 012), and Answer Generator (spec 013) can each consume it without requiring changes to this spec's contract. Additive optional fields preserve backward compatibility. Breaking changes require a schema version increment.
- **SC-008**: The Planner can switch domains (field pack swap) without code changes, verified by running the same query with two different field packs and observing different strategy and constraint outputs.
- **SC-009**: `RetrievalPlan` contains no retrieval-engine-specific artifacts (no SQL, no index identifiers, no BM25 expressions, no embedding configuration), verified by schema inspection and integration test assertions.
- **SC-010**: A new `StrategyType` value can be introduced by adding it to a field pack YAML without modifying any Planner source file.
- **SC-011**: A `RetrievalPlan` produced by Planner version N MUST remain consumable by Retrieval Engine version N+1 unless a documented major schema version change has occurred. Backward-compatible additions (new optional fields) are preferred over breaking changes. Breaking changes require a schema version increment and explicit migration documentation.

---

## Assumptions

- The Planner receives a pre-parsed or raw query string; query preprocessing (tokenization, spell correction) is handled upstream by the Query Analysis layer.
- `ChunkSet` outputs from spec 007 and `KnowledgePackage` outputs from spec 008 are available as metadata references during entity resolution but are NOT queried at plan time.
- Field packs follow the same YAML configuration mechanism established by spec 002; no new configuration format is introduced.
- The Retrieval Engine V2 (spec 010) is the primary consumer of `RetrievalPlan`; the contract is designed for extension to specs 011–013 without breaking changes.
- `planner_confidence` is a heuristic score derived from intent clarity and entity resolution success; it is not a trained ML probability.
- All `StrategyType` values in the initial vocabulary (FR-014) are selectable by the Planner; the Retrieval Engine V2 does not need to implement all strategies on day one, but the Planner must be able to produce plans containing any of them.
- Query analysis (upstream) produces a structured representation that the Planner consumes; the exact interface between query analysis and the Planner is defined in this spec's pipeline contract.
- The Planner is a synchronous, CPU-bound, stateless component; async wrappers may be added at the integration boundary without changing core planning logic.
- `ExecutionHints` are advisory — no behavior changes are required if a Retrieval Engine ignores them entirely.
- `PlannerDiagnostics` are stripped from production API responses by default; infrastructure for toggling diagnostics on/off is a deployment concern, not a Planner concern.
