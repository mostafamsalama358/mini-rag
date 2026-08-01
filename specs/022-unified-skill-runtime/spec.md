# Feature Specification: Unified Skill Runtime

**Feature Branch**: `022-unified-skill-runtime`

**Created**: 2026-07-28

**Status**: Draft

**Input**: User description: "Feature 022 — Unified Skill Runtime. Complete migration from legacy Skill execution to a true unified Skill runtime. Remove remaining architectural debt from Feature 021 so Skills become the single execution model across the RAG engine. Architectural refactor with backward-compatible public API."

---

## Summary

Feature **021** made Domain Skills Skill-first on the legacy answer path. Feature **022** completes that migration: Skills run exclusively through the **unified pipeline**, `SkillExecutionContext` is the sole execution contract, legacy Skill bypass is removed, the QueryPlan metadata bridge disappears for Skill traffic, retrieval strategies become real plugins, shared runtime stays domain-agnostic, and the runtime is structured so future workflow stages can be added without rewriting executors.

This is an **architectural refactor**. External clients keep the same Skill IDs, Skill packs, UI selection, and additive `skill_id` request behavior. Frozen answer **response** contracts remain unchanged.

**Architecture stance (normative)**: Unified Skill Runtime remains a **Domain Pack capability on the sole Answer + Retrieval path (016)**. Per **ADR-022-001**, Domain Skills are **configuration for the Unified Runtime**—they do not own a separate execution pipeline. This feature does **not** create a Skill Service, parallel answer path, Skill-specific pipeline family, or new sole owner. Exception ADR required only if a dedicated Skill owner or separate Skill runtime is later proposed.

---

## Relationship to Existing Features

| Feature | Relationship |
|---------|--------------|
| **021 Domain Skill Framework** | Dependency and completion vehicle. 021 introduced Skills, profiles, SkillExecutionContext, entity-only parse, and strategy keys. 022 eliminates remaining debt (legacy bypass, QueryPlan bridge, stub strategies, answer_service monolith, residual domain coupling). |
| **ADR-022-001** | Binding decision: Skills configure the Unified Runtime; rejected legacy/separate/dual/Skill-specific pipelines. |
| **016 Architecture Consolidation** | Binding. One production execution path. Skills configure that path; they do not fork it. M0 freeze: no parallel Skill runtime. |
| **015 Unified Pipeline Migration** | Binding. Unified pipeline becomes the **only** Skill execution pipeline. Frozen `/answer` response field-level contract preserved. Additive request `skill_id` unchanged. |
| **002 Field Registry / Domain Packs** | Skills and Metadata Profiles remain pack-owned. Engine loads Domain → Skill → Profile → Strategy → Prompt only. |
| **004 Semantic Query Parser** | Under Skill: entity/slot extraction only (021). Non-Skill domains may retain full semantic parse via the same unified pipeline stages. |
| **009 / 010** | Retrieval consumes SkillExecutionContext (filters + strategy) directly—not QueryPlan field/operation bridges. |
| **011 / 012 / 013** | Evidence, context, and generation remain sole-path stages; Skill supplies prompt reference, optional response schema, and citation policy as context attributes. |
| **018 / 019** | Quality and evaluation contracts unchanged; Skill identity remains a quality-trace / eval-scope attribute. |
| **020 Pharmacy Recommendation** | Remains pack capability invoked only via explicit recommend Skill; shared runtime must not hardcode pharmacy recommend imports. |

**Non-goals (explicit):**

- No new Skills or new domains in this feature.
- No response-schema validation product work unless required to keep the runtime contract intact.
- No citation-enforcement product improvements beyond preserving optional citation policy on the execution context.
- No redesign of ingest/chunking (006 / 017).
- No new public Skill API or Skill microservice.
- No automatic Skill detection (021 rules remain).

---

## Design Principles

1. **One pipeline** — Skill traffic and non-Skill traffic share the unified execution pipeline; Skill selection configures stages, it does not choose a second executor.
2. **Context is the contract** — Downstream stages receive `SkillExecutionContext` (when a Skill is bound); they must not require a QueryPlan field/operation bridge for Skill execution.
3. **No legacy Skill bypass** — Domains with Skills must not be forced onto a legacy answer executor.
4. **Strategies are plugins** — Retrieval behavior is selected only from the execution context strategy key; the engine must not branch on domain field names.
5. **Domain packs own domain knowledge** — Shared runtime never embeds pharmacy/legal field names or pack module imports.
6. **Modular executors** — Oversized answer orchestration is split into stage executors with clear interfaces.
7. **Workflow-ready** — Stage composition must allow inserting validation, clarification, post-validation, and formatting stages without rewriting existing executors.
8. **Compatibility first** — Migration is internal; API, UI, Skill IDs, packs, and existing Skill tests remain valid.

---

## Canonical Runtime Flow

When a Skill is selected:

```
Request (additive skill_id)
  → Resolve Skill
  → Build SkillExecutionContext
  → Unified Pipeline (stage chain)
       Validation → Entity Parse → Retrieval (strategy plugin)
       → Rerank → Generation (Skill prompt) → Format
  → Response (frozen external contract)
```

When a domain has no Skills (e.g. generic):

```
Request
  → Unified Pipeline (full semantic understanding where configured)
  → Response
```

There is **no** Skill → Legacy Executor path.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Same Skill Answers, Single Runtime Path (Priority: P1)

As a pharmacy (or other Skill-enabled domain) user, I select a Skill and ask a question. I receive the same class of answer I get today (correct Skill behavior, clarifications when required, citations when retrieval is used), without any visible change to buttons, Skill names, or request shape—while all Skill traffic runs on one platform execution path.

**Why this priority**: Proves the migration is complete for the primary product surface without regressing 021 behavior.

**Independent Test**: Select each existing pharmacy starter Skill, ask a representative question, confirm Skill-bound behavior and frozen response fields; verify platform telemetry/trace shows unified pipeline (not legacy Skill bypass).

**Acceptance Scenarios**:

1. **Given** a Skill-enabled project and a selected Skill, **When** the user asks a valid question, **Then** the system answers using that Skill’s profile, validation, retrieval strategy, and prompt—without requiring a second executor path.
2. **Given** a Skill that requires entities (e.g. medicine pair), **When** the user omits required entities, **Then** the system returns a clarification consistent with existing Skill validation behavior.
3. **Given** the public answer request with additive `skill_id`, **When** the client sends the same payload as today, **Then** the response preserves the frozen external answer contract.

---

### User Story 2 - Operators Trust One Execution Model (Priority: P1)

As a platform operator, I can reason about Skill traffic as a single pipeline: Skill resolution produces one execution context that every downstream stage consumes. I no longer need to maintain a special-case legacy Skill executor or a QueryPlan field bridge for Skill requests.

**Why this priority**: Removes the dual-runtime operational risk identified after 021.

**Independent Test**: Architecture/governance checks confirm Skill-enabled packs do not route to a legacy Skill executor; Skill stages do not depend on QueryPlan field/operation for capability routing.

**Acceptance Scenarios**:

1. **Given** a domain pack that declares Skills, **When** an answer request includes a valid `skill_id`, **Then** execution uses only the unified pipeline.
2. **Given** a Skill-bound request, **When** retrieval runs, **Then** filters and strategy come from SkillExecutionContext—not from a Skill-authored or bridge-derived QueryPlan field/operation.
3. **Given** platform diagnostics for a Skill request, **When** an operator inspects the run, **Then** Skill id, profile id, and strategy are visible as first-class execution attributes.

---

### User Story 3 - Strategy Behavior Is Explicit and Distinct (Priority: P2)

As a domain pack author, I configure a Metadata Profile’s retrieval strategy and get meaningfully different retrieval behavior for `default`, `semantic_only`, `hybrid`, `document_lookup`, and `pair_lookup`—without the engine knowing my domain’s field names.

**Why this priority**: Stub strategies were a major 021 debt item; real plugins unlock pack evolution without engine edits.

**Independent Test**: For each minimum strategy key, bind a Skill/profile and verify retrieval path/behavior differs as specified for that strategy (including structured pair lookup for `pair_lookup`).

**Acceptance Scenarios**:

1. **Given** a profile with `retrieval_strategy: pair_lookup`, **When** entities are present, **Then** structured pair/document lookup is attempted before generic vector fallback.
2. **Given** profiles with `semantic_only` vs `hybrid` vs `document_lookup` vs `default`, **When** otherwise identical Skill requests run, **Then** each strategy produces its defined retrieval behavior (not identical aliases of a single path).
3. **Given** shared runtime code, **When** searched for domain field names used as strategy switches, **Then** no engine branch selects strategy by hardcoded domain field labels.

---

### User Story 4 - Modular, Workflow-Ready Runtime (Priority: P2)

As a platform engineer, I can add or reorder Skill workflow stages (e.g. post-validation before formatting) by composing stage interfaces—without editing a monolithic answer service or existing stage executors’ internals.

**Why this priority**: Enables future Skill workflows without another debt cycle.

**Independent Test**: Demonstrate that answer orchestration is split into dedicated stage executors with interfaces; adding a no-op stage in the Skill workflow does not require modifying unrelated executors’ core logic.

**Acceptance Scenarios**:

1. **Given** the Skill runtime, **When** a request is processed, **Then** validation, entity parsing, retrieval, generation, and response formatting are handled by dedicated executors (not one oversized answer module owning all stages inline).
2. **Given** a future need for an additional Skill stage, **When** the stage implements the stage interface and is registered in the workflow composition, **Then** existing executors remain unchanged aside from composition wiring.
3. **Given** non-Skill domains, **When** they answer questions, **Then** they still use the unified pipeline with appropriate understanding stages—not a revived legacy Skill bypass.

---

### User Story 5 - Domain-Agnostic Shared Runtime (Priority: P2)

As a multi-domain platform owner, I can load pharmacy or other packs without the shared runtime importing or hardcoding pharmacy-specific modules, field names, or leaflet/interaction vocabulary.

**Why this priority**: Required for true Domain Pack plug-in readiness and 016 domain independence.

**Independent Test**: Static/architecture scan of shared runtime shows no pack-specific imports or hardcoded domain field vocabulary used for control flow; domain behavior is reached only through pack interfaces.

**Acceptance Scenarios**:

1. **Given** shared runtime modules, **When** inspected for static pack imports, **Then** there are none of the form “import pharmacy pack internals.”
2. **Given** Skill retrieval and generation, **When** domain-specific helpers are needed, **Then** they are invoked only via Domain Pack interfaces resolved from the active domain.
3. **Given** a non-pharmacy Skill pack (e.g. legal stubs), **When** a Skill is selected, **Then** the same unified Skill runtime executes without pharmacy-only code paths.

---

### Edge Cases

- Missing or unknown `skill_id` on a Skill-required domain: refuse/clarify as today (021)—never silently classify or fall back to legacy.
- Skill references a missing Metadata Profile: fail closed with a clear Skill resolution error.
- Strategy key unknown: fail closed or use an explicit documented default policy (must not silently alias without logging).
- Empty retrieval after strategy execution: preserve existing no-context / clarification user outcomes.
- Domains with zero Skills: unified pipeline without Skill context; must not force Skill selection.
- Concurrent Skill and client metadata filters: Skill profile filters remain authoritative; client filters merge without silently broadening Skill constraints (021 no-silent-broaden preserved).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST execute all Skill-bound answer requests exclusively through the unified pipeline (no Skill → legacy executor path).
- **FR-002**: System MUST remove forced legacy execution for packs that declare Skills.
- **FR-003**: System MUST treat `SkillExecutionContext` as the sole Skill execution contract passed through Skill workflow stages.
- **FR-004**: `SkillExecutionContext` MUST carry at least: Skill definition, Metadata Profile, metadata filters, parsed entities, validation rules, retrieval strategy, prompt reference/content binding, optional response schema, and optional citation policy.
- **FR-005**: For Skill-bound requests, retrieval and related stages MUST NOT require `QueryPlan.field` / `QueryPlan.operation` or profile `plan_field` / `plan_operation` bridges.
- **FR-006**: System MUST remove Skill QueryPlan bridge fields (`plan_field`, `plan_operation`) from the Skill runtime contract once consumers no longer need them.
- **FR-007**: System MUST decompose oversized answer orchestration into dedicated stage executors with interfaces (validation, entity parse, retrieval, generation, response formatting at minimum).
- **FR-008**: Retrieval strategy selection MUST come only from `SkillExecutionContext`; shared runtime MUST NOT select strategy via hardcoded domain field names.
- **FR-009**: System MUST provide real, distinct plugin implementations for at least: `default`, `semantic_only`, `hybrid`, `document_lookup`, and `pair_lookup`.
- **FR-010**: Shared runtime MUST NOT statically depend on pharmacy pack modules or hardcode pharmacy/interaction/dosage/leaflet control-flow vocabulary.
- **FR-011**: Domain-specific behavior MUST be reachable only through Domain Pack interfaces loaded for the active domain.
- **FR-012**: Skill runtime composition MUST support adding workflow stages without modifying existing stage executor internals (composition/wiring only).
- **FR-013**: Public API compatibility MUST be preserved: additive `skill_id`, frozen answer response contract, existing Skill IDs, packs, and UI Skill selection.
- **FR-014**: Existing Skill behavioral tests and architecture gates MUST be updated only as needed for internal migration and MUST continue to pass for preserved external behavior.
- **FR-015**: After implementation, an architecture audit MUST be produced by inspecting actual code paths (not documentation alone), using the validation checklist in this feature’s planning artifacts.
- **FR-016**: System MUST implement ADR-022-001: Skills configure the Unified Runtime and MUST NOT own a separate execution pipeline (legacy Skill executor, separate Skill runtime, dual runtime, or Skill-specific pipelines are forbidden).
- **FR-017**: Every pipeline stage MUST declare an explicit contract covering input, output, failure conditions, and side effects; stages MUST communicate only through immutable objects and MUST NOT mutate outputs produced by previous stages.
- **FR-018**: Every pipeline stage MUST be independently testable against its stage contract.
- **FR-019**: `SkillExecutionContext` MUST be immutable; stages MAY enrich execution state only by producing a derived context or a dedicated stage result—shared mutable execution state is forbidden.
- **FR-020**: Retrieval strategies MUST be true plugins resolved via a Strategy Registry to a `RetrievalStrategy` execute contract; the engine MUST NOT branch on strategy names (`if strategy == …` / `switch(strategy)` forbidden in shared runtime).
- **FR-021**: Adding a retrieval strategy MUST require only a strategy implementation plus registration—no shared-engine modification.
- **FR-022**: The pipeline MUST support declarative stage registration (Pipeline Builder → register stage → execute); adding a stage MUST NOT require editing orchestrator core logic beyond composition/registration.
- **FR-023**: Architecture tests MUST enforce major 022 rules and FAIL when violated (pharmacy pack imports in shared runtime; reachable legacy Skill executor; QueryPlan bridge return; engine strategy-name branching; engine domain-field-name branching; new strategy requiring engine edits; mutation of `SkillExecutionContext`).
- **FR-024**: Feature completion REQUIRES that answer orchestration is no longer owned by a single God-object answer service; request flow MUST be Skill Resolver → Pipeline Orchestrator → registered stages → Response.
- **FR-025**: System MUST document and support extension points for workflow stages, retrieval strategies, and response formatters such that new extensions require registration only (no engine edits).

### Key Entities *(include if feature involves data)*

- **SkillExecutionContext**: Immutable execution unit for a Skill-bound request; sole contract for Skill workflow stages.
- **Skill Workflow / Stage Chain**: Ordered composition of stage executors that consume the context and produce stage outputs toward a frozen external answer response.
- **Stage Executor**: Interface-backed unit responsible for one Skill runtime concern (validation, entity parse, retrieval, generation, formatting, etc.).
- **Stage Contract**: Declared input, output, failure conditions, and side effects for a stage; basis for independent stage tests.
- **Stage Result**: Immutable per-stage output; used to derive further context without mutating prior outputs.
- **Pipeline Builder / Stage Registry**: Declarative registration surface for composing the unified runtime stage chain.
- **Retrieval Strategy Plugin**: Named retrieval behavior resolved from the execution context via Strategy Registry; pack-agnostic at the engine boundary.
- **Strategy Registry**: Maps strategy keys to plugin implementations; sole resolution path for retrieval behavior.
- **Response Formatter Plugin**: Registered formatter extension (e.g. markdown, json, clinical, citation_only) selected without engine edits.
- **Domain Pack Interface**: Boundary through which domain-specific helpers are loaded without shared-runtime pack imports.
- **ADR-022-001**: Architecture decision that Skills are Unified Runtime configuration, not pipeline owners.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture layer boundaries and 016 sole-path ownership rules.
- **NFR-002**: I/O-bound operations MUST be async; public APIs MUST include type hints.
- **NFR-003**: External providers (LLM, embedding, vector DB, reranker) MUST remain swappable via existing factory interfaces.
- **NFR-004**: RAG answer paths MUST return source citations when retrieval is used (existing behavior preserved).
- **NFR-005**: Project/system and Skill prompts MUST remain versioned/pack-owned when modified.
- **NFR-006**: Unit and integration tests MUST cover migrated Skill runtime behavior and architecture constraints.
- **NFR-007**: Structured logging MUST include correlation identifiers and Skill/profile/strategy attributes at service boundaries.
- **NFR-008**: Secrets MUST NOT be stored in source control.
- **NFR-009**: Migration MUST be incremental-safe: no intentional public API breaks; dual paths are transitional only if required for cutover and MUST be removed before feature completion (no permanent legacy Skill bypass).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Skill-bound answer requests in Skill-enabled domains execute on the unified pipeline (0 Skill requests routed to a legacy Skill executor).
- **SC-002**: For Skill-bound requests, retrieval and capability routing depend only on the Skill execution context (filters + strategy)—0 remaining dependency on a separate field/operation plan bridge.
- **SC-003**: Each of the five minimum retrieval strategies exhibits distinct, documented retrieval behavior under controlled fixtures (not identical alias behavior).
- **SC-004**: Shared runtime scan reports 0 static pharmacy-pack imports and 0 hardcoded pharmacy field-name strategy/control branches.
- **SC-005**: Skill answer orchestration is modular: validation, entity parse, retrieval, generation, and formatting are separable stage responsibilities (not one inseparable monolith).
- **SC-006**: Existing public Skill selection UX and Skill IDs continue to work without client changes; frozen answer response fields remain populated as today for golden Skill scenarios.
- **SC-007**: Existing Skill regression suite (021 behavioral + architecture tests, updated for internal moves) remains green at feature completion.
- **SC-008**: A post-implementation architecture audit answers “Can Domain Skills be considered a fully first-class runtime architecture?” with evidence from actual code paths, scoring checklist items PASS/PARTIAL/FAIL.
- **SC-009**: Architecture test suite fails closed on each major 022 rule violation listed in FR-023 (verified by intentional negative fixtures or equivalent static assertions).
- **SC-010**: Declarative stage registration is demonstrated by composing the Skill workflow without editing orchestrator internals when adding a registered no-op/extension stage.
- **SC-011**: Strategy Registry resolves all minimum strategies via plugin execute() with 0 strategy-name branches in shared engine control flow.
- **SC-012**: Feature completion checklist is 100% true: single Unified Runtime; legacy Skill executor removed; QueryPlan bridge removed; SkillExecutionContext sole execution contract; true strategy plugins; declarative stage registration; domain-independent shared runtime; answer_service no longer God-object orchestrator; architecture tests enforce major rules; public API backward compatible.

---

## Assumptions

- Feature 021 Skill packs, starter Skill IDs, Metadata Profiles, UI Skill buttons, and additive `skill_id` remain the compatibility baseline.
- Frozen `/answer` response contract from 015 remains binding; 022 does not redesign external response fields.
- Non-Skill domains continue to answer via the unified pipeline without requiring Skill selection.
- “Real” strategies may share low-level search primitives but MUST differ in composition (e.g. hybrid fuses channels; semantic_only does not; document_lookup prioritizes document-scoped retrieval; pair_lookup uses structured pair fetch with fallback).
- Workflow-ready means stage composition extensibility; implementing every future stage (clarification loops, post-validation products, citation enforcement products, tool invocation) is out of scope unless required to remove the monolith or satisfy stage-registration architecture.
- Extension point catalogs (formatters such as clinical/citation_only; strategies such as keyword_only/graph) document supported registration surfaces; shipping every listed extension implementation is not required for 022 completion unless needed to prove the plugin model (minimum strategies in FR-009 remain mandatory).
- Pharmacy recommendation (020) remains available only through explicit recommend Skills and pack interfaces.
- Post-implementation architecture audit is a required validation deliverable, not optional documentation.
- ADR-022-001 is normative for Skills-as-configuration vs Skills-as-pipeline-owner.

---

## Deliverables

- Architecture refactor of Skill runtime onto the unified pipeline
- ADR-022-001 (Skills as Unified Runtime configuration)
- Updated runtime stage executors, stage contracts, and retrieval strategy plugins
- Declarative pipeline stage registration / Pipeline Builder
- Strategy Registry with true plugins (no engine strategy-name branching)
- Enforceable architecture tests for major 022 rules
- Documented extension points (workflow stages, retrieval strategies, response formatters)
- Updated tests (behavioral compatibility + architecture gates)
- Migration notes describing removed legacy bypass, QueryPlan bridge removal, God-object elimination, and operator-visible diagnostics changes
- Post-implementation architecture audit report (checklist in feature validation)

---

## Additional Architecture Requirements *(merged 2026-07-28)*

These requirements **extend** the sections above. They do not replace FR-001–FR-015 or SC-001–SC-008.

### A1. ADR-022-001 — Skills Configure the Unified Runtime

**Decision**: Domain Skills become configuration for the Unified Runtime rather than owning their own execution pipeline.

**Rejected alternatives**: Legacy Skill Executor; Separate Skill Runtime; Dual Runtime; Skill-specific Pipelines.

**Reasoning**: single execution model; single ownership; lower maintenance cost; easier testing; better plugin architecture; future workflow stages become reusable.

Normative record: `governance/adr-022-001-skills-as-unified-runtime-configuration.md`.

### A2. Stage Contracts

Every pipeline stage MUST explicitly define:

- Input
- Output
- Failure conditions
- Side effects

Rules:

- Stages MUST communicate only through immutable objects.
- Stages MUST never mutate outputs produced by previous stages.
- Every stage MUST be independently testable against its contract.

### A3. Immutable Execution Context

- `SkillExecutionContext` MUST be immutable.
- Pipeline stages MAY enrich execution state only by producing a **derived context** or a **dedicated stage result**.
- Shared mutable execution state is **forbidden**.

### A4. Retrieval Strategy Registry

Retrieval strategies MUST be true plugins.

Required resolution path:

```
StrategyRegistry → RetrievalStrategy → Execute()
```

Forbidden in shared engine control flow:

- `if strategy == …`
- `switch(strategy)` (or equivalent name-branching)

Adding a new retrieval strategy MUST require only:

1. Strategy implementation
2. Registration

No engine modification.

### A5. Pipeline Stage Registration

The pipeline MUST support declarative stage registration.

Desired composition model:

```
PipelineBuilder → Register Stage → Execute
```

Adding a stage MUST NOT require editing orchestrator core logic (registration/composition only).

Future stages MAY include (registration surfaces; not all required to ship in 022):

- Validation
- Clarification
- Entity Parsing
- Retrieval
- Reranking
- Prompt Resolution
- Generation
- Post Validation
- Formatting
- Citation Enforcement
- Guardrails
- Tool Invocation

### A6. Architecture Tests (Enforceable)

Architecture rules MUST be enforceable by tests that fail when violated. Examples that MUST FAIL:

| Violation | Expected test outcome |
|-----------|----------------------|
| Shared runtime imports `fields.pharmacy.*` | FAIL |
| Legacy Skill executor becomes reachable for Skill traffic | FAIL |
| QueryPlan bridge returns / is required for Skill execution | FAIL |
| Engine branches on strategy names | FAIL |
| Engine branches on domain field names | FAIL |
| New strategy requires engine modification (beyond registration) | FAIL |
| Pipeline stages mutate `SkillExecutionContext` | FAIL |

Documentation-only architecture rules are insufficient for feature completion.

### A7. God Object Elimination

Feature is **not complete** until answer orchestration is no longer owned by a single God-object answer service.

Target flow:

```
Request
  → Skill Resolver
  → Pipeline Orchestrator
  → Validation Stage
  → Entity Parsing Stage
  → Retrieval Stage
  → Generation Stage
  → Formatting Stage
  → Response
```

No single service SHOULD coordinate the entire runtime inline.

### A8. Extension Points

Supported extension points MUST be documented. New extensions SHOULD require **registration only** (no engine edits).

**Workflow stages** (examples): Validation; Clarification; Safety; Guardrails; Tool Invocation; Formatter; Citation Enforcement.

**Retrieval strategies** (examples / surfaces): `semantic_only`; `hybrid`; `pair_lookup`; `document_lookup`; `keyword_only`; `graph` (plus mandatory minimum set in FR-009 including `default`).

**Response formatters** (examples / surfaces): `markdown`; `json`; `clinical`; `citation_only`.

### A9. Updated Completion Gate

Feature 022 is complete only when **all** of the following are true:

1. Single Unified Runtime
2. Legacy Skill executor removed
3. QueryPlan bridge removed
4. SkillExecutionContext is sole execution contract
5. Retrieval strategies are true plugins
6. Pipeline stages are declaratively registered
7. Shared runtime is domain-independent
8. answer_service no longer acts as God object
9. Architecture tests enforce all major architectural rules
10. Existing public API remains backward compatible

This gate is mirrored by **SC-012** and the post-implementation architecture audit.
