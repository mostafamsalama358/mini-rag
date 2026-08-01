# Research: Unified Skill Runtime

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

Phase 0 decisions resolving planning unknowns. Aligns with [spec.md](./spec.md) and [ADR-022-001](./governance/adr-022-001-skills-as-unified-runtime-configuration.md).

---

## R1 — Skills as Unified Runtime configuration (not pipeline owners)

**Decision**: Domain Skills configure the Unified Runtime via immutable `SkillExecutionContext`. They do not own a legacy executor, separate Skill runtime, dual runtime, or Skill-specific pipeline family (ADR-022-001).

**Rationale**: Spec completion gate; 016 M0; extends ADR-021-001 (capability, not service) to execution topology.

**Alternatives considered**:
- Keep Skill→legacy force in `pipeline/router.py` — rejected (permanent dual runtime)
- Separate Skill Runtime package/service — rejected (new path/owner)
- Skill-specific pipelines per Skill family — rejected (N pipelines; blocks reusable stages)
- Skills as Unified Runtime configuration (**selected**)

---

## R2 — Remove Skill→legacy force; native unified binding

**Decision**: Delete the pack-has-skills branch that routes to `legacy_executor`. Unified pipeline resolves `skill_id` → `SkillExecutionContext` and runs registered Skill-aware stages. Legacy executor must not be reachable for Skill traffic at feature completion (may remain temporarily for non-Skill cutover only if required, then removed from Skill paths before done).

**Rationale**: FR-001/FR-002/SC-001; current code comment in `router.py` explicitly deferred Skill binding to legacy.

**Alternatives considered**:
- Shadow dual-run Skill on unified vs legacy — rejected as permanent posture (transitional only if tasks require, must exit before completion)
- Feature flag forever — rejected (SC-012)

---

## R3 — Remove QueryPlan bridge for Skill execution

**Decision**: Remove `plan_field` / `plan_operation` from SkillFilterProfile / SkillExecutionContext as required Skill execution inputs. Retrieval, validation, and generation under Skill consume `SkillExecutionContext` (filters, strategy, prompt_ref, entities, validation, citation_policy, response_schema). Non-Skill domains may still use QueryPlan from full semantic parse.

**Rationale**: FR-005/FR-006/SC-002; bridge reintroduced domain field vocabulary into the engine.

**Alternatives considered**:
- Keep bridge “for capability checks only” — rejected (engine still knows field names)
- Replace QueryPlan entirely platform-wide — rejected (out of scope; non-Skill path still needs understanding output)
- Context-only for Skill; QueryPlan for non-Skill (**selected**)

---

## R4 — Stage contracts + immutable enrichment

**Decision**: Each stage declares Input / Output / Failure / Side effects. Communication via immutable objects only. Stages never mutate prior outputs or `SkillExecutionContext`; enrichment via `replace`-style derived context or dedicated `StageResult`.

**Rationale**: FR-017–FR-019 / A2–A3; enables independent tests and workflow insertion.

**Alternatives considered**:
- Mutable shared bag on pipeline context — rejected (hidden coupling)
- Giant answer_service locals — rejected (God object)

---

## R5 — Strategy Registry without engine name-branching

**Decision**: `StrategyRegistry.get(name) → RetrievalStrategy.execute(ctx, ports…)`. Engine/retrieval stage calls registry only. Forbidden: `if strategy == "pair_lookup"` (or domain field switches) in shared runtime. Minimum real plugins: `default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup` (distinct composition, not aliases).

**Rationale**: FR-020/FR-021/SC-003/SC-011; aligns with existing `RetrieverRegistry` / `StrategyRouter` patterns in `core/retrieval_engine` without conflating Skill strategy keys with engine retriever ids.

**Alternatives considered**:
- Keep answer_service strategy ifs — rejected (A4)
- Map strategies onto QueryPlan.field — rejected (bridge)
- Registry + execute plugins (**selected**)

**Note**: Reuse low-level ports (`search_vector`, `fetch_pair_documents` via Domain Pack interface) injected into strategy execute—strategies stay domain-agnostic.

---

## R6 — Declarative PipelineBuilder

**Decision**: `PipelineBuilder.register(stage)…build()` produces ordered stage chain. Orchestrator executes registered chain. Adding a stage = implement contract + register; no orchestrator core edits.

**Rationale**: FR-022/SC-010/A5; workflow-ready for clarification, guardrails, tools, citation enforcement later.

**Alternatives considered**:
- Hardcoded `await validate; await parse; …` in one function — rejected (extension requires edits)
- Plugin framework with dynamic import discovery only — optional later; explicit registration sufficient for 022

---

## R7 — God-object elimination boundary

**Decision**: Feature incomplete while `RAGService.answer_question` (or equivalent) owns Skill validation+parse+retrieval+generation+format inline. Target: Skill Resolver → Pipeline Orchestrator → registered stages → Response. `answer_service` may remain a thin facade for DI/wiring or non-Skill helpers, but must not be the Skill orchestration owner.

**Rationale**: FR-024/A7/SC-012; constitution Feature-First / SOLID.

**Alternatives considered**:
- “Extract helpers but keep answer_question as conductor” — rejected (still God object)
- Full rewrite of all NLP routes — rejected (scope); facade OK

---

## R8 — Domain independence enforcement

**Decision**: Shared runtime (`services/rag/**`, `services/rag/pipeline/**`, shared skill runtime, core answer path) MUST NOT statically import `fields.pharmacy.*` or branch on pharmacy field tokens (`interactions`, `dosage`, `leaflet`, …) for control flow. Domain helpers load via pack interfaces (`domain_helpers` / Domain Pack ports). Architecture tests fail on regressions.

**Rationale**: FR-010/FR-011/FR-023/SC-004; 021 left residual coupling (`fetch_interaction_documents` naming, pair strategy ifs, parser domain string).

**Alternatives considered**:
- Rename-only without interfaces — insufficient
- Allow “known pharmacy” in engine — rejected

---

## R9 — Architecture tests as completion requirement

**Decision**: Ship `tests/architecture/test_022_*.py` that fail closed on ADR/spec rules (imports, reachable legacy Skill path, QueryPlan bridge, strategy-name branching, domain-field branching, context mutation, strategy-requires-engine-edit heuristic). Documentation-only rules are insufficient (A6).

**Rationale**: FR-023/SC-009/SC-012.

**Alternatives considered**:
- Manual audit only — rejected (spec A6)
- Lint without tests — insufficient alone

---

## R10 — Compatibility and non-goals

**Decision**: Preserve additive `skill_id`, Skill IDs, packs, UI buttons, frozen response fields. Do not ship new Skills/domains, citation enforcement product, or response-schema validation product unless required for runtime contracts. Extension catalogs document registration surfaces; shipping every formatter/strategy example is not required beyond the mandatory five strategies.

**Rationale**: Spec non-goals + FR-013/SC-006.

---

## R11 — Relationship to 015 pipeline modes

**Decision**: Skill-enabled traffic uses unified pipeline execution (not legacy Skill bypass). Existing 015 mode resolver (`legacy`/`unified`/`shadow`/`canary`) continues for platform cutover, but **Skill packs must not special-case to legacy**. When platform mode is unified (or sole path post-015), Skills run natively there.

**Rationale**: Avoid redefining 015 modes; remove only the Skill-specific force-legacy branch.

**Alternatives considered**:
- Force unified globally in 022 — may exceed scope; prefer removing Skill bypass and requiring Skill path = unified stages regardless of branding of executor module
- Keep force-legacy until 015 complete — rejected by 022 success criteria
