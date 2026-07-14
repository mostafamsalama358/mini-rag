# Tasks: Retrieval Planner

**Input**: Design documents from `specs/009-retrieval-planner/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Required per constitution (Principle VII). All user stories include test tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths are included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the package skeleton so all subsequent tasks have valid import paths.

- [X] T001 Create `src/core/retrieval_planner/` directory tree with `__init__.py` files for all sub-packages: `intent/`, `entities/`, `filters/`, `strategies/`, `clarification/`, `limits/`
- [X] T002 Create `tests/unit/core/retrieval_planner/__init__.py` (empty marker for pytest discovery)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, interfaces, registry, and field pack that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `src/core/retrieval_planner/errors.py` — define `RetrievalPlannerError` (base), `PlannerConfigError`, `StrategyNotFoundError`, `PlanAssemblyError`; all extend `RetrievalPlannerError`
- [X] T004 Create `src/core/retrieval_planner/models.py` — open types and enumerations: `StrategyType = Annotated[str, Field(min_length=1)]`, `IntentCategory` Literal, `OutputShapeType` Literal (data-model.md §0)
- [X] T005 Add to `src/core/retrieval_planner/models.py` — primary value models with `frozen=True`: `QueryIntent`, `ResolvedEntity`, `QueryFilter`, `OutputShape` (data-model.md §1–3, §7); include deterministic `filter_id` computation
- [X] T006 Add to `src/core/retrieval_planner/models.py` — execution contract models with `frozen=True`: `RetrievalLimits` (max_evidence_units, max_candidates, scope), `RetrievalConstraints` (latency_budget_ms, cost_budget, freshness_window, required_language, citation_required), `ExecutionHints` (all optional fields; not frozen at construction, frozen by outer model) (data-model.md §4–6)
- [X] T007 Add to `src/core/retrieval_planner/models.py` — internal and identity models: `PlannerDiagnostics` (`frozen=False`), `RetrievalPlanMetadata` (`frozen=True`, plan_id via SHA256 per research R4) (data-model.md §8–9)
- [X] T008 Add to `src/core/retrieval_planner/models.py` — `RetrievalPlan` (frozen=True, all fields per data-model.md §10); add model validator: when `clarification_required=True` assert `retrieval_strategies` is empty and `clarification_question` is non-empty; when `False` assert `retrieval_strategies` non-empty and `clarification_question` is None
- [X] T009 Add to `src/core/retrieval_planner/models.py` — `RetrievalPlannerConfig` with all fields and defaults from data-model.md §11 (strategy ids, available_strategies list, clarification_confidence_threshold=0.5, citation_required=True, diagnostics_enabled=False)
- [X] T010 Create `src/core/retrieval_planner/interfaces.py` — all six ABCs: `IRetrievalPlanner`, `IIntentClassifier`, `IEntityResolver`, `IFilterExtractor`, `IStrategySelector`, `IClarificationDetector`; signatures per data-model.md §12; import `ParseResult` from `core.query_parser.schema`
- [X] T011 Create `src/core/retrieval_planner/registry.py` — `RetrievalPlannerRegistry` with per-interface `register_*` methods and `build_pipeline(config) -> RetrievalPlannerPipeline`; raise `StrategyNotFoundError` on unknown ids (data-model.md §14)
- [X] T012 [P] Create `src/fields/generic/retrieval_planning.yaml` — initial generic field pack: `available_strategies` (full 9-value list), `default_strategy: semantic`, `clarification_confidence_threshold: 0.5`, `citation_required: true`, `diagnostics_enabled: false`, `budget_defaults` table per research R10, placeholder `strategy_mappings` (factual → [semantic, hybrid] only; remaining mappings added in Phase 5), `entity_aliases: {}`, `entity_type_patterns: []`, `default_latency_budget_ms: null`
- [X] T013 [P] Create `tests/unit/core/retrieval_planner/conftest.py` — shared `ParseResult` fixtures covering six cases: clear factual (ibuprofen contraindications), ambiguous (tell me about it), tabular (dosage table for aspirin), keyword (list all drug interactions), multi-intent (compare and list), empty query; each fixture as a named pytest fixture using `core.query_parser.schema.ParseResult`

**Checkpoint**: Foundation ready — all models, interfaces, registry, field pack, and test fixtures exist. User story implementation can begin.

---

## Phase 3: User Story 1 — Deterministic Plan from Unambiguous Query (Priority: P1) 🎯 MVP

**Goal**: A clear factual query produces a fully populated, immutable `RetrievalPlan` with correct intent, entities, ordered strategies, limits, constraints, and zero retrieval execution.

**Independent Test**: `pytest tests/unit/core/retrieval_planner/test_plan_assembler.py -k factual` — plan has `clarification_required=False`, non-empty `retrieval_strategies`, `planner_confidence >= 0.8`, same `plan_id` across two invocations.

### Tests (write first, verify they fail before implementation)

- [X] T014 [P] [US1] Create `tests/unit/core/retrieval_planner/test_models.py` — verify: `RetrievalPlan` raises on field mutation (frozen); `StrategyType` accepts any non-empty string; `plan_id` starts with `"rp_"` and is 19 chars; `schema_version` is `"1.0.0"`; `RetrievalPlan` validator raises when `clarification_required=True` and `retrieval_strategies` is non-empty; static import scan of `src/core/retrieval_planner/` asserts no import of `core.retrieval`, `stores.vectordb`, `stores.llm`, or any SQL driver (SC-006)
- [X] T015 [P] [US1] Create `tests/unit/core/retrieval_planner/test_intent_classifier.py` — for each `QueryPlan.operation` value verify correct `IntentCategory`; verify text-pattern overrides (tabular, procedural, comparative, navigational); verify `confidence` values per research R5 (1.0 for exact, 0.8 for pattern, 0.6/0.4 for unsupported)
- [X] T016 [P] [US1] Create `tests/unit/core/retrieval_planner/test_entity_resolver.py` — entities list wraps to `ResolvedEntity`; alias resolution uses config; `entity_id` deterministic; empty entities list → empty output; `canonical_form` defaults to `raw_text` when no alias found
- [X] T017 [P] [US1] Create `tests/unit/core/retrieval_planner/test_filter_extractor.py` — explicit filters from `query_plan.filters` produce `QueryFilter` with `source="explicit"`; language filter always added as `source="implicit"` from `query_plan.language`; `filter_id` is deterministic

### Implementation

- [X] T018 [P] [US1] Create `src/core/retrieval_planner/intent/rule_based.py` — `RuleBasedIntentClassifier(IIntentClassifier)` with `classifier_id="rule_based"`; implement two-pass logic: Pass 1 operation→IntentCategory table, Pass 2 text-pattern augmentation; assign confidence values per research R5; populate `evidence` with matching phrases; populate `secondary_categories` with other possible intents
- [X] T019 [P] [US1] Create `src/core/retrieval_planner/entities/query_plan_resolver.py` — `QueryPlanEntityResolver(IEntityResolver)` with `resolver_id="query_plan"`; wrap `ParseResult.query_plan.entities` into `ResolvedEntity`; apply alias lookup from `config.entity_aliases`; assign `entity_type` via `config.entity_type_patterns` keyword matching; compute deterministic `entity_id`
- [X] T020 [P] [US1] Create `src/core/retrieval_planner/filters/query_plan_extractor.py` — `QueryPlanFilterExtractor(IFilterExtractor)` with `extractor_id="query_plan"`; wrap `ParseResult.query_plan.filters` dict into `QueryFilter` list; add implicit language `QueryFilter` from `query_plan.language`; compute deterministic `filter_id`
- [X] T021 [P] [US1] Create `src/core/retrieval_planner/limits/budget_estimator.py` — `BudgetEstimator` (not an ABC; internal); `estimate(intent, config) -> RetrievalLimits`; look up `config.budget_defaults[intent.category]` for `max_evidence_units`, `max_candidates`, `scope`; apply any field pack ceiling
- [X] T022 [US1] Create `src/core/retrieval_planner/assembly.py` — `ConstraintsBuilder.build(filters, config) -> RetrievalConstraints`; `HintsBuilder.build(intent, entities, constraints) -> ExecutionHints | None` per research R13; `OutputShapeDeriver.derive(intent) -> OutputShape`; `PlanAssembler.assemble(...) -> RetrievalPlan` composing all sub-objects, computing `plan_id`, setting `schema_version="1.0.0"`, setting `diagnostics=None` when `diagnostics_enabled=False`
- [X] T023 [US1] Create `src/core/retrieval_planner/pipeline.py` — `RetrievalPlannerPipeline(IRetrievalPlanner)`: constructor injects all six stage instances plus `BudgetEstimator` and `PlanAssembler`; `plan()` runs 7 stages in order per data-model.md §13; no instance state mutated between calls (NFR-004)
- [X] T024 [US1] Create `tests/unit/core/retrieval_planner/test_plan_assembler.py` — using factual fixture: assert full plan shape (all required fields, correct types); assert `plan_id` identical on two invocations with same input; assert `clarification_required=False`, `retrieval_strategies` non-empty, `planner_confidence >= 0.8`; assert `retrieval_constraints.citation_required=True`; assert `diagnostics=None`

**Checkpoint**: US1 complete — factual query produces a valid, deterministic `RetrievalPlan`. Test `pytest tests/unit/core/retrieval_planner/ -k "models or intent or entity or filter or assembler"`.

---

## Phase 4: User Story 2 — Ambiguous Query Triggers Clarification (Priority: P2)

**Goal**: Vague/low-confidence queries set `clarification_required=True`, return a non-empty `clarification_question`, and emit an empty `retrieval_strategies` list.

**Independent Test**: `pytest tests/unit/core/retrieval_planner/test_clarification_detector.py` — ambiguous fixture produces `clarification_required=True`, non-empty `clarification_question`, empty `retrieval_strategies`.

### Tests (write first)

- [X] T025 [P] [US2] Create `tests/unit/core/retrieval_planner/test_clarification_detector.py` — test all three trigger conditions: (1) upstream `needs_clarification=True` propagates `clarification_prompt`; (2) `intent.confidence < threshold` triggers with question mentioning secondary_categories; (3) empty `canonical_query` triggers; test non-trigger: clear query with confidence ≥ threshold does NOT trigger (≥ 85% precision guard per SC-005)

### Implementation

- [X] T026 [US2] Create `src/core/retrieval_planner/clarification/confidence_based.py` — `ConfidenceBasedClarificationDetector(IClarificationDetector)` with `detector_id="confidence_based"`; implement three-condition logic per research R9: check upstream flag first, then intent confidence vs `config.clarification_confidence_threshold`, then empty query; return `(True, question_str)` or `(False, None)`; generate clarification question from `intent.secondary_categories` when condition 2 triggers
- [X] T027 [US2] Update `src/core/retrieval_planner/pipeline.py` — when `clarification_required=True`: skip `strategy_selector.select()` (return `[]`); set `planner_confidence` to `intent.confidence`; log `clarification_trigger` in diagnostics; ensure `PlanAssembler` receives empty strategies list and clarification state
- [X] T028 [US2] Update `tests/unit/core/retrieval_planner/test_plan_assembler.py` — add ambiguous fixture assertions: `clarification_required=True`, `retrieval_strategies==()`, `clarification_question` non-empty, `planner_confidence <= 0.5`

**Checkpoint**: US2 complete — ambiguous queries are gated. Test `pytest tests/unit/core/retrieval_planner/ -k "clarification or assembler"`.

---

## Phase 5: User Story 3 — Ordered Strategy Selection Based on Query Type (Priority: P2)

**Goal**: Different query types produce different ordered `retrieval_strategies` lists; ordering expresses Planner intent; Retrieval Engine may reorder at runtime.

**Independent Test**: `pytest tests/unit/core/retrieval_planner/test_strategy_selector.py` — factual query yields `semantic` first; tabular query yields `table` first; keyword query yields `keyword` or `metadata` first; multi-intent query yields more than one strategy.

### Tests (write first)

- [X] T029 [P] [US3] Create `tests/unit/core/retrieval_planner/test_strategy_selector.py` — test all seven `IntentCategory` values against the generic strategy_mappings table; test that a strategy excluded from `available_strategies` is absent from output; test fallback to `config.default_strategy` when all mapped strategies are excluded; test multi-strategy output for `mixed` intent; test SC-010: add `"citations_graph"` to a custom config's `available_strategies` and verify it appears in output without any code change

### Implementation

- [X] T030 [US3] Create `src/core/retrieval_planner/strategies/config_driven.py` — `ConfigDrivenStrategySelector(IStrategySelector)` with `selector_id="config_driven"`; look up `config.strategy_mappings[intent.category]`; filter against `config.available_strategies`; if result empty fall back to `[config.default_strategy]`; return ordered `list[StrategyType]`; record excluded strategies in diagnostic trace when `diagnostics_enabled`
- [X] T031 [US3] Update `src/fields/generic/retrieval_planning.yaml` — complete `strategy_mappings` table for all seven `IntentCategory` values per research R8 (factual, list, comparative, procedural, tabular, navigational, mixed)
- [X] T032 [US3] Update `src/core/retrieval_planner/registry.py` — register all five default implementations (`RuleBasedIntentClassifier`, `QueryPlanEntityResolver`, `QueryPlanFilterExtractor`, `ConfigDrivenStrategySelector`, `ConfidenceBasedClarificationDetector`) as defaults; `build_pipeline()` resolves by id and constructs `RetrievalPlannerPipeline`

**Checkpoint**: US3 complete — strategy selection works for all intent types. Test `pytest tests/unit/core/retrieval_planner/ -k "strategy or selector"`.

---

## Phase 6: User Story 4 — Domain-Agnostic Configuration (Priority: P3)

**Goal**: Swapping a field pack changes strategy availability, budget ceilings, and confidence thresholds without any Planner code change.

**Independent Test**: Load pharmacy pack, load generic pack with same query — `retrieval_strategies` and `retrieval_limits` differ between the two runs; neither output contains domain-specific code logic.

### Tests (write first)

- [X] T033 [P] [US4] Update `tests/unit/core/retrieval_planner/test_strategy_selector.py` — add domain-pack switch tests: load a restricted config (excludes `graph`), assert `graph` never in output; load config with lower `max_evidence_units` ceiling, assert `retrieval_limits.max_evidence_units` respects ceiling; assert same query with two packs produces different primary strategies

### Implementation

- [X] T034 [P] [US4] Create `src/fields/legal/retrieval_planning.yaml` — legal domain overrides: exclude `graph` and `table` from `available_strategies`, raise `clarification_confidence_threshold` to `0.7`, set lower `max_evidence_units` ceiling (e.g., 8), set `default_strategy: semantic`
- [X] T035 [P] [US4] Create `src/fields/pharmacy/retrieval_planning.yaml` — pharmacy domain overrides: restrict `available_strategies` to `[semantic, keyword, metadata, table, hybrid]`, set `entity_type_patterns` for drug/dosage/contraindication entities, set `budget_defaults.tabular.max_evidence_units: 5`
- [X] T036 [US4] Update `tests/unit/core/retrieval_planner/test_plan_assembler.py` — add domain config integration test: run factual fixture under generic config, run again under a restricted config, assert `retrieval_strategies` and `retrieval_limits` differ, no Planner source file change required

**Checkpoint**: US4 complete — domain switching works. All four user stories independently testable. Test `pytest tests/unit/core/retrieval_planner/`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Golden test suite, observability, static validation, and final integration check.

- [X] T037 [P] Create `tests/integration/test_retrieval_planner_golden.py` — 15+ labelled query fixtures asserting: `intent.category` matches expected label; primary `retrieval_strategies[0]` matches expected strategy; `clarification_required` matches ambiguity label; `metadata.plan_id` identical across two invocations; ≥ 90% strategy accuracy across the suite (SC-004); `--benchmark` flag runs 100× per fixture and asserts p95 ≤ 50 ms (SC-002)
- [X] T038 [P] Add no-retrieval-imports assertion to `tests/unit/core/retrieval_planner/test_models.py` — walk `src/core/retrieval_planner/` with `ast` / `importlib`, assert no import of `core.retrieval`, `stores.vectordb`, `stores.llm`, or any known vector/SQL driver module (SC-006)
- [X] T039 [P] Add SC-010 and SC-011 tests to `tests/unit/core/retrieval_planner/test_models.py` — SC-010: build a `RetrievalPlannerConfig` with `"citations_graph"` in `available_strategies` and a mapping, run pipeline, assert `"citations_graph"` in output without any code change; SC-011: assert `metadata.schema_version == "1.0.0"` and matches `MAJOR.MINOR.PATCH` regex on every plan produced by golden fixtures
- [X] T040 Update `src/core/retrieval_planner/pipeline.py` — add structured logging at planner boundary using existing `logging` infrastructure: log at INFO level on plan completion with fields `query_id` (from `ParseResult` hash), `intent_category`, `strategies`, `planner_confidence`, `latency_ms`; log at WARNING when clarification triggered; log at DEBUG when diagnostics enabled (NFR-011)
- [X] T041 [P] Run `pytest tests/unit/core/retrieval_planner/ -v` and confirm all unit tests pass; run `pytest tests/integration/test_retrieval_planner_golden.py -v` and confirm ≥ 90% golden accuracy and ≥ 85% clarification precision (SC-004, SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — independent of US2/US3/US4
- **US2 (Phase 4)**: Depends on Phase 2 + US1 pipeline (T023 modifies pipeline.py) — run after US1
- **US3 (Phase 5)**: Depends on Phase 2 — can run in parallel with US2 after US1 assembler is complete
- **US4 (Phase 6)**: Depends on US3 (strategy_mappings in field pack must be complete) — run after US3
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on other stories
- **US2 (P2)**: Requires US1 pipeline.py to exist (T027 modifies it) — start after T023 completes
- **US3 (P2)**: Requires Phase 2 only — can be developed in parallel with US2 by a second developer
- **US4 (P3)**: Requires US3 field pack and strategy selector — start after US3 complete

### Within Each User Story

1. Write test stubs first (verify they fail — red)
2. Implement default components (parallel where marked [P])
3. Wire pipeline / assembler (sequential)
4. Verify tests pass (green)
5. Checkpoint validation before moving to next story

### Parallel Opportunities

| Group | Tasks |
|---|---|
| Foundational models (different logical sections of same file, write sequentially) | T004 → T005 → T006 → T007 → T008 → T009 |
| Foundational support files (different files) | T010 [P], T011 [P], T012 [P], T013 [P] |
| US1 test stubs (different files) | T014 [P], T015 [P], T016 [P], T017 [P] |
| US1 default implementations (different files) | T018 [P], T019 [P], T020 [P], T021 [P] |
| US3/US2 concurrency | US2 (T025–T028) and US3 (T029–T032) after US1 |
| US4 domain packs (different files) | T034 [P], T035 [P] |
| Polish (different files) | T037 [P], T038 [P], T039 [P], T041 [P] |

---

## Parallel Example: User Story 1

```bash
# After Phase 2 complete, launch US1 test stubs in parallel:
Task T014: test_models.py
Task T015: test_intent_classifier.py
Task T016: test_entity_resolver.py
Task T017: test_filter_extractor.py

# Then launch US1 default implementations in parallel:
Task T018: intent/rule_based.py
Task T019: entities/query_plan_resolver.py
Task T020: filters/query_plan_extractor.py
Task T021: limits/budget_estimator.py

# Then sequential wiring:
Task T022: assembly.py (depends on T018–T021)
Task T023: pipeline.py (depends on T022)
Task T024: test_plan_assembler.py full assertions
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T013) — CRITICAL
3. Complete Phase 3: User Story 1 (T014–T024)
4. **STOP and VALIDATE**: `pytest tests/unit/core/retrieval_planner/ -k "models or intent or entity or filter or assembler"`
5. A functioning deterministic Retrieval Planner is available for Retrieval Engine V2 (spec 010) to consume

### Incremental Delivery

1. Setup + Foundational → package skeleton, all models and interfaces
2. US1 → deterministic planning for factual queries (**MVP**)
3. US2 → ambiguity gate (prevents bad retrievals)
4. US3 → strategy selection for all query types
5. US4 → domain switching (pharmacy, legal field packs)
6. Polish → golden suite, observability, static analysis validation

### Parallel Team Strategy

With two developers after Phase 2:
- **Developer A**: US1 (T014–T024) → US2 (T025–T028)
- **Developer B**: US3 (T029–T032) → US4 (T033–T036)
- Polish (T037–T041) together after all stories complete

---

## Notes

- `[P]` tasks write to different files — safe to parallelize within the same phase
- `[Story]` label maps each task to its user story for traceability
- Models in Phase 2 (T004–T009) are sequential — each adds to the same `models.py` file
- Tests must be written first and observed to fail before each implementation phase
- `RetrievalPlan` is immutable once assembled — no test should mutate a returned plan
- `PlannerDiagnostics` is `None` in all unit tests by default (`diagnostics_enabled=False` in fixture configs)
- SC-010 extensible strategy test (T039) must pass with zero modifications to any `src/core/retrieval_planner/` file
