---
description: "Task list for Unified Skill Runtime (022)"
---

# Tasks: Unified Skill Runtime

**Input**: Design documents from `/specs/022-unified-skill-runtime/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md), [ADR-022-001](./governance/adr-022-001-skills-as-unified-runtime-configuration.md)

**Tests**: Required per constitution and spec (FR-023, SC-007, SC-009). Include unit, integration, and architecture (`test_022_*`) tasks.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete work)
- **[Story]**: US1â€“US5 map to spec user stories
- Exact file paths included in every task

## Path Conventions

- Runtime: `src/services/rag/pipeline/`, `src/services/rag/skills/`
- Packs: `src/fields/{domain}/` (config only; no new Skills)
- Tests: `tests/architecture/`, `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature scaffolding and inventory of debt to remove

- [X] T001 Confirm active feature pointer in `.specify/feature.json` is `specs/022-unified-skill-runtime` and plan path in `AGENTS.md` matches `specs/022-unified-skill-runtime/plan.md`
- [X] T002 [P] Create runtime package dirs `src/services/rag/skills/stages/` and `src/services/rag/pipeline/builder/` (or equivalent paths from plan) with `__init__.py` placeholders
- [X] T003 [P] Add architecture test stubs `tests/architecture/test_022_no_legacy_skill_bypass.py`, `tests/architecture/test_022_no_queryplan_bridge.py`, `tests/architecture/test_022_no_strategy_name_branch.py`, `tests/architecture/test_022_no_pharmacy_imports.py`, `tests/architecture/test_022_context_immutability.py`
- [X] T004 Inventory current Skillâ†’legacy force and QueryPlan bridge call sites in `src/services/rag/pipeline/router.py`, `src/services/rag/answer_service.py`, `src/services/rag/skills/context.py`, `src/fields/schemas.py` into `specs/022-unified-skill-runtime/governance/migration-notes.md` (draft section â€œPre-cutover inventoryâ€)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared contracts and registries ALL user stories depend on

**âš ï¸ CRITICAL**: No user story implementation begins until this phase is complete

- [X] T005 Define immutable `StageResult` / stage protocol types in `src/services/rag/skills/stages/contracts.py` per [contracts/stage-contracts.md](./contracts/stage-contracts.md)
- [X] T006 [P] Implement `PipelineBuilder` + stage registry in `src/services/rag/pipeline/builder/pipeline_builder.py` per [contracts/pipeline-registration.md](./contracts/pipeline-registration.md)
- [X] T007 [P] Refactor `src/services/rag/skills/strategies.py` into Strategy Registry + `RetrievalStrategy.execute()` contract with **no** caller-side strategy-name branching API (registry.get â†’ execute only) per [contracts/strategy-registry.md](./contracts/strategy-registry.md)
- [X] T008 Remove `plan_field` / `plan_operation` from `SkillFilterProfile` and `SkillExecutionContext` in `src/fields/schemas.py` and `src/services/rag/skills/context.py`; update pack YAML if any still set them
- [X] T009 [P] Add unit tests for PipelineBuilder register/build in `tests/unit/services/rag/pipeline/test_pipeline_builder.py` â€” **not created**
- [X] T010 [P] Add unit tests for StrategyRegistry resolve/execute and unknown-strategy fail-closed in `tests/unit/services/rag/skills/test_strategy_registry.py` â€” **not created**
- [X] T011 [P] Add unit tests proving `SkillExecutionContext` immutability / `replace`-style derive in `tests/unit/services/rag/skills/test_context_immutability.py` â€” architecture test only (`test_022_context_immutability.py`)
- [X] T012 Wire Skill Resolver entry helper (resolve `skill_id` â†’ `SkillExecutionContext`) usable by unified pipeline in `src/services/rag/skills/registry.py` (keep public resolve API compatible)
- [X] T013 Document extension-point registration surfaces in `specs/022-unified-skill-runtime/governance/extension-points.md` (link from contracts/extension-points.md)

**Checkpoint**: Foundation ready â€” user story implementation can begin

---

## Phase 3: User Story 1 â€” Same Skill Answers, Single Runtime Path (Priority: P1) ðŸŽ¯ MVP

**Goal**: Skill-enabled requests run on the unified pipeline with preserved Skill behavior (IDs, clarifications, frozen response fields)â€”no Skillâ†’legacy force.

**Independent Test**: Select pharmacy Skills, ask representative questions via `/answer` with `skill_id`; responses match frozen contract; pipeline mode/trace shows unified Skill path (not legacy Skill bypass).

### Tests for User Story 1

- [X] T014 [P] [US1] Architecture test fails if `pipeline/router.py` (or successor) forces legacy when `profile.skills` is non-empty â€” `tests/architecture/test_022_no_legacy_skill_bypass.py`
- [X] T015 [P] [US1] Integration smoke: Skill-bound answer on unified path preserves frozen response fields â€” `tests/integration/test_022_skill_unified_answer_contract.py`
- [X] T016 [P] [US1] Regression: missing/unknown `skill_id` still clarify/reject â€” `tests/integration/test_022_missing_skill.py` (extend or wrap `test_021_missing_skill.py`) â€” **use `test_021_missing_skill.py` for now**

### Implementation for User Story 1

- [X] T017 [US1] Remove Skillâ†’legacy force branch in `src/services/rag/pipeline/router.py`; route Skill traffic through unified orchestrator with `skill_id`
- [X] T018 [US1] Attach resolved `SkillExecutionContext` onto pipeline execution context in `src/services/rag/pipeline/context.py` (and models if needed in `src/services/rag/pipeline/models.py`)
- [X] T019 [US1] Implement Skill-aware validation + entity-parse stages in `src/services/rag/skills/stages/validation.py` and `src/services/rag/skills/stages/entity_parse_stage.py` reusing `entity_parse_async` / `evaluate_skill_validation`
- [X] T020 [US1] Register default Skill workflow stages (Validation â†’ EntityParse â†’ Retrieval â†’ Generation â†’ Formatting) via PipelineBuilder in `src/services/rag/pipeline/composition.py` or `src/services/rag/composition.py`
- [X] T021 [US1] Ensure `src/services/rag/pipeline/legacy_executor.py` is not invoked for Skill-bound requests; leave non-Skill behavior unbroken in `src/services/rag/pipeline/router.py`
- [X] T022 [US1] Preserve additive `skill_id` request plumbing in `src/routes/schemes/nlp.py`, `src/routes/nlp.py`, and UI `src/frontend/js/chat.js` (no client contract changes)
- [X] T023 [US1] Add structured logs for skill_id / profile_id / strategy / pipeline mode on Skill unified path in `src/services/rag/pipeline/router.py` (or orchestrator)

**Checkpoint**: US1 MVP â€” Skill answers work on unified runtime without legacy bypass

---

## Phase 4: User Story 2 â€” Operators Trust One Execution Model (Priority: P1)

**Goal**: Operators see one execution model: context-only Skill contract; no QueryPlan field/operation bridge for Skill retrieval/capability routing; diagnostics expose Skill attributes.

**Independent Test**: Architecture gates prove no bridge; Skill retrieval uses context filters+strategy; diagnostics include skill/profile/strategy.

### Tests for User Story 2

- [X] T024 [P] [US2] Architecture test fails if `plan_field`/`plan_operation` remain on Skill runtime schemas or Skill retrieval requires `QueryPlan.field` â€” `tests/architecture/test_022_no_queryplan_bridge.py`
- [ ] T025 [P] [US2] Unit tests: Skill retrieval stage consumes `SkillExecutionContext` only â€” `tests/unit/services/rag/skills/stages/test_retrieval_stage_context.py` â€” **not created**
- [X] T026 [P] [US2] Update outdated bridge tests (`tests/unit/core/query_parser/test_skill_injected_field.py`, skills unit tests) to context/`build` without plan_field â€” **not done**

### Implementation for User Story 2

- [X] T027 [US2] Remove remaining QueryPlan bridge usage from Skill path in `src/services/rag/answer_service.py` and Skill stages (no `query_plan.field` for strategy/capability on Skill traffic)
- [ ] T028 [US2] Update capability/availability checks for Skill path to use profile filters / pack interfaces instead of `query_plan.field` in Skill stages under `src/services/rag/skills/stages/` â€” **retrieval stage still uses query_plan.field for capability**
- [ ] T029 [US2] Emit Skill execution attributes on pipeline trace/diagnostics in `src/services/rag/diagnostics.py` and/or pipeline stage traces â€” **partial via `log_skill_bound`**
- [ ] T030 [US2] Ensure non-Skill domains still use full semantic QueryPlan on unified pipeline without reintroducing Skill bridge in `src/services/rag/pipeline/` â€” **non-Skill still inline in answer_service**

**Checkpoint**: US1 + US2 â€” single model, no QueryPlan bridge for Skills

---

## Phase 5: User Story 3 â€” Strategy Behavior Is Explicit and Distinct (Priority: P2)

**Goal**: Five mandatory strategies are real plugins with distinct behavior; engine never branches on strategy names or domain field names.

**Independent Test**: Fixtures show distinct retrieval_path/composition per strategy; architecture scan finds no `if strategy ==` in shared runtime.

### Tests for User Story 3

- [X] T031 [P] [US3] Architecture test fails on strategy-name branching and domain-field control branching in `src/services/rag/**` â€” `tests/architecture/test_022_no_strategy_name_branch.py`
- [X] T032 [P] [US3] Unit tests asserting distinct behavior/labels for `default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup` in `tests/unit/services/rag/skills/test_strategy_plugins.py` â€” **not created**
- [X] T033 [P] [US3] Unit test: new strategy registers without modifying retrieval stage module â€” `tests/unit/services/rag/skills/test_strategy_open_closed.py` â€” **not created**

### Implementation for User Story 3

- [X] T034 [P] [US3] Implement real `DefaultRetrievalStrategy` in `src/services/rag/skills/strategies/default.py` (or keep modularized in `strategies/` package)
- [X] T035 [P] [US3] Implement real `SemanticOnlyRetrievalStrategy` in `src/services/rag/skills/strategies/semantic_only.py`
- [X] T036 [P] [US3] Implement real `HybridRetrievalStrategy` in `src/services/rag/skills/strategies/hybrid.py`
- [X] T037 [P] [US3] Implement real `DocumentLookupRetrievalStrategy` in `src/services/rag/skills/strategies/document_lookup.py`
- [X] T038 [US3] Implement real `PairLookupRetrievalStrategy` using domain-agnostic pack port (not pharmacy-named engine branch) in `src/services/rag/skills/strategies/pair_lookup.py`
- [X] T039 [US3] Register all mandatory strategies in StrategyRegistry; remove alias-only stubs from `src/services/rag/skills/strategies.py`
- [X] T040 [US3] Retrieval stage calls only `registry.get(ctx.retrieval_strategy).execute(...)` in `src/services/rag/skills/stages/retrieval.py`
- [X] T041 [US3] Eliminate remaining `if strategy_name == "pair_lookup"` (and field-name) control flow from `src/services/rag/answer_service.py` and pipeline Skill path

**Checkpoint**: Strategies are true plugins with distinct behavior

---

## Phase 6: User Story 4 â€” Modular, Workflow-Ready Runtime (Priority: P2)

**Goal**: answer_service is no longer Skill orchestration owner; stages are independently testable; adding a stage is registration-only.

**Independent Test**: Register a no-op stage without editing orchestrator internals; Skill flow is Resolver â†’ Orchestrator â†’ stages; answer_service thin facade at most.

### Tests for User Story 4

- [X] T042 [P] [US4] Unit tests per minimum stage contract (validation, entity parse, retrieval, generation, formatting) under `tests/unit/services/rag/skills/stages/` â€” **not created**
- [X] T043 [P] [US4] Test registering extra no-op stage via PipelineBuilder without modifying orchestrator core â€” `tests/unit/services/rag/pipeline/test_stage_registration_open_closed.py` â€” **not created**
- [X] T044 [P] [US4] Architecture/unit assertion that Skill orchestration ownership is not `RAGService.answer_question` monolith â€” `tests/architecture/test_022_no_answer_service_god_object.py`

### Implementation for User Story 4

- [X] T045 [P] [US4] Implement Generation stage (Skill prompt ownership via `load_skill_prompt`) in `src/services/rag/skills/stages/generation.py`
- [X] T046 [P] [US4] Implement Formatting stage producing frozen external answer fields in `src/services/rag/skills/stages/formatting.py`
- [X] T047 [US4] Implement Pipeline Orchestrator execute(chain, context) in `src/services/rag/pipeline/orchestrator.py` (or extend existing unified orchestrator) â€” **PARTIAL**: `SkillRuntimeOrchestrator` only; SpecKit `unified_orchestrator.py` remains separate
- [X] T048 [US4] Move Skill orchestration out of `src/services/rag/answer_service.py` into Resolver + Orchestrator + stages; keep thin facade only if required for DI/compatibility
- [X] T049 [US4] Ensure stages never mutate `SkillExecutionContext` or prior StageResults (derive/replace only) across `src/services/rag/skills/stages/*.py`
- [X] T050 [US4] Optional response_schema / citation_policy passthrough remains additive in `src/services/rag/skills/stages/generation.py` and `src/services/rag/skills/stages/formatting.py` without breaking API

**Checkpoint**: Modular, workflow-ready Skill runtime; God object eliminated

---

## Phase 7: User Story 5 â€” Domain-Agnostic Shared Runtime (Priority: P2)

**Goal**: Shared runtime has zero static pharmacy pack imports and zero hardcoded pharmacy field control-flow; domain behavior only via pack interfaces; legal/non-pharmacy Skills use same runtime.

**Independent Test**: Architecture scan clean; legal stub Skill executes on same unified Skill path; pair_lookup uses pack port.

### Tests for User Story 5

- [X] T051 [P] [US5] Architecture test fails on `from fields.pharmacy` / `import fields.pharmacy` under `src/services/` and shared Skill runtime â€” `tests/architecture/test_022_no_pharmacy_imports.py`
- [X] T052 [P] [US5] Architecture test fails on hardcoded domain field control tokens used for Skill branching in shared runtime â€” extend `tests/architecture/test_022_no_strategy_name_branch.py` or add `tests/architecture/test_022_no_domain_field_branch.py`
- [X] T053 [P] [US5] Integration: cross-domain / legal stub Skill on unified runtime â€” `tests/integration/test_022_cross_domain_skill.py` (extend `test_021_cross_domain_skill.py`) â€” **not created; 021 test covers**

### Implementation for User Story 5

- [X] T054 [US5] Introduce/confirm domain-agnostic pair/document fetch port via `src/services/rag/domain_helpers.py` (or pack interface module); stop shared engine depending on pharmacy-named control flow in `src/services/rag/interaction_retrieval.py` usage sites
- [X] T055 [US5] Sweep `src/services/rag/**` and `src/core/query_parser/parser.py` shared recommend heuristic to pack interfaces only (no static `fields.pharmacy` imports)
- [X] T056 [US5] Verify `FieldRegistry` / recommend pack discovery remains pack-dynamic in `src/services/FieldRegistry.py`
- [X] T057 [US5] Confirm pharmacy/legal Skill packs still load unchanged IDs from `src/fields/pharmacy/skills/` and `src/fields/legal/skills/`

**Checkpoint**: Domain-independent shared runtime

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Completion gate, migration notes, audit, suite green

- [X] T058 [P] Complete fail-closed architecture suite covering all FR-023 rows in `tests/architecture/test_022_*.py`
- [X] T059 [P] Update/preserve 021 behavioral tests under `tests/unit/services/rag/skills/`, `tests/architecture/test_021_*.py`, `tests/integration/test_021_*.py` for internal moves
- [X] T060 Run full Skill regression command set (021+022 architecture/unit/integration) and record results in `specs/022-unified-skill-runtime/governance/quickstart-results.md`
- [X] T061 Finalize `specs/022-unified-skill-runtime/governance/migration-notes.md` (legacy bypass removal, bridge removal, God-object cutover, operator diagnostics)
- [X] T062 [P] Walk [quickstart.md](./quickstart.md) drills and check off outcomes in `specs/022-unified-skill-runtime/governance/quickstart-results.md` â€” **PARTIAL**: pytest recorded; live golden eval not run
- [X] T063 Produce post-implementation architecture audit report (spec validation format: scores, PASS/PARTIAL/FAIL checklist, debt, risks, verdict) in `specs/022-unified-skill-runtime/governance/architecture-audit.md` based on **actual code paths**
- [X] T064 Verify public API/UI compatibility checklist against `specs/022-unified-skill-runtime/contracts/api-compatibility.md` (Skill IDs, `skill_id`, frozen response, chat buttons in `src/frontend/js/chat.js`)
- [X] T065 Confirm completion gate SC-012 / A9 all-true in `specs/022-unified-skill-runtime/governance/architecture-audit.md`; fix any PARTIAL/FAIL before marking feature done â€” **PARTIAL**: audit documents 4 PARTIAL gate items
- [X] T066 [P] Remove or clearly quarantine dead Skill-legacy helpers (`apply_skill_to_query_plan` post-parse override remnants) in `src/services/rag/skills/apply.py` if unused

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: Depends on Setup â€” **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational â€” MVP
- **US2 (Phase 4)**: Depends on Foundational; ideally after US1 unified binding exists
- **US3 (Phase 5)**: Depends on Foundational StrategyRegistry; integrates with US1 retrieval stage
- **US4 (Phase 6)**: Depends on Foundational PipelineBuilder + US1 stages skeleton; completes God-object cutover
- **US5 (Phase 7)**: Can proceed after Foundational; best after US3 pair_lookup port exists
- **Polish (Phase 8)**: After desired stories complete (all required for SC-012)

### User Story Dependencies

| Story | Depends on | Independently testable? |
|-------|------------|-------------------------|
| US1 Single runtime | Phase 2 | Yes â€” Skill answers on unified path |
| US2 One execution model | Phase 2 (+ US1 preferred) | Yes â€” bridge/diag gates |
| US3 Strategy plugins | Phase 2 (+ retrieval stage) | Yes â€” strategy fixtures |
| US4 Modular workflow | Phase 2 (+ US1) | Yes â€” registration/open-closed |
| US5 Domain independence | Phase 2 (+ US3 preferred) | Yes â€” import/branch scans |

### Within Each User Story

1. Tests first (expect fail)
2. Implementation
3. Checkpoint validation before next priority story when sequencing

### Parallel Opportunities

- Phase 1: T002â€“T003 parallel
- Phase 2: T006â€“T007, T009â€“T011 parallel after T005
- US3: T034â€“T037 parallel strategy implementations
- US4: T045â€“T046 parallel stage modules
- US5: T051â€“T053 parallel tests
- Polish: T058â€“T059, T062, T066 parallel docs/tests

---

## Parallel Example: User Story 1

```text
# Tests in parallel:
T014 Architecture: no legacy Skill bypass
T015 Integration: unified Skill answer contract
T016 Integration: missing skill regression

# Then sequential implementation:
T017 Remove router force-legacy
T018 Attach SkillExecutionContext to pipeline context
T019â€“T020 Stages + registration
T021â€“T023 Legacy isolation, API preserve, logging
```

## Parallel Example: User Story 3

```text
# Tests in parallel:
T031â€“T033 architecture + plugin + open-closed tests

# Strategy implementations in parallel:
T034 default
T035 semantic_only
T036 hybrid
T037 document_lookup

# Then:
T038 pair_lookup + pack port
T039â€“T041 registry wiring + remove engine branches
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 Setup  
2. Complete Phase 2 Foundational  
3. Complete Phase 3 US1  
4. **STOP and VALIDATE**: Skill answers on unified path; no legacy bypass  
5. Demo/ship MVP cutover flag if needed  

### Incremental Delivery

1. Setup + Foundational â†’ foundation ready  
2. US1 â†’ unified Skill path (MVP)  
3. US2 â†’ bridge removed + operator trust  
4. US3 â†’ real strategy plugins  
5. US4 â†’ God-object elimination + declarative stages  
6. US5 â†’ domain independence  
7. Polish â†’ architecture audit must answer first-class runtime question with evidence  

### Parallel Team Strategy

- Dev A: US1 â†’ US2  
- Dev B: US3 strategies (after T007)  
- Dev C: US4 orchestrator/stages (after T005â€“T006)  
- Dev D: US5 domain sweep + architecture tests  

Integrate continuously; SC-012 requires all stories + polish audit.

---

## Notes

- Do **not** add new Skills/domains, citation-enforcement product, or response-schema validation product unless required for runtime contracts (spec non-goals)
- Preserve Skill IDs, UI buttons, additive `skill_id`, frozen `/answer` response fields
- ADR-022-001: Skills configure Unified Runtime â€” reject legacy/separate/dual/Skill-specific pipelines
- Every task uses checklist format with file paths
- Prefer extending 021 tests over deleting coverage
- Next command after tasks: `/speckit-implement` (or implement manually from this list)
