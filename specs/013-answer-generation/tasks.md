# Tasks: Answer Generation (spec 013)

**Input**: Design documents from `specs/013-answer-generation/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅ · quickstart.md ✅

**Tests**: Required per constitution (Principle VII) — unit and integration tests included for every user story.

**Organization**: Grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Parallelizable (different files, no incomplete dependencies)
- **[US#]**: User story this task belongs to (maps to spec.md)

---

## Phase 1: Setup (Package Structure)

**Purpose**: Create the module skeleton so all Phase 2 tasks can run in parallel.

- [X] T001 Create `src/core/answer_generation/` package with all sub-package `__init__.py` stubs — `src/core/answer_generation/__init__.py`, `composition/__init__.py`, `parsing/__init__.py`, `citation/__init__.py`, `grounding/__init__.py`
- [X] T002 [P] Populate field-pack YAML stubs for all three domains — `src/fields/generic/answer_generation.yaml`, `src/fields/legal/answer_generation.yaml`, `src/fields/pharmacy/answer_generation.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, config, and interfaces that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Implement domain models (AnswerResult, CitationReference, GroundingFlag, ComposedPrompt, CapabilityModule) — `src/core/answer_generation/models.py`
- [X] T004 [P] Implement error hierarchy (AnswerGenerationError, SchemaVersionError, CitationResolutionError) — `src/core/answer_generation/errors.py`
- [X] T005 [P] Implement AnswerGenerationConfig Pydantic model with load_config_from_yaml, merge_config, and resolve_answer_generation_config (generic < domain < project) — `src/core/answer_generation/config.py`
- [X] T006 Implement all four abstract interfaces (IPromptComposer, IOutputParser, ICitationFormatter, IGroundingChecker) — `src/core/answer_generation/interfaces.py`
- [X] T007 [P] Create test package `__init__.py` and conftest.py with reusable Context, Citation, ContextBlock, and ConflictGroup fixtures — `tests/unit/core/answer_generation/__init__.py`, `tests/unit/core/answer_generation/conftest.py`

**Checkpoint**: Foundation complete — all Phase 3 tasks can now start in parallel.

---

## Phase 3: User Story 1 — Cited Answer from Valid Context (Priority: P1) 🎯 MVP

**Goal**: A non-empty `Context` with a valid `citation_map` produces an `AnswerResult`
where every cited claim maps to a valid `CitationReference`.

**Independent Test**:
```bash
pytest tests/unit/core/answer_generation/ -v -k "not conflict and not no_answer and not grounding"
pytest tests/integration/test_answer_generation_e2e.py::test_cited_answer_happy_path -v
```

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement DefaultPromptComposer: embed ordered blocks with `[item_id]` markers, append system instructions and capability modules sorted by priority — `src/core/answer_generation/composition/default_composer.py`
- [X] T009 [P] [US1] Implement JsonOutputParser: attempt JSON parse first, fall back to plain-text; return `(answer_text, confidence_note)` tuple — `src/core/answer_generation/parsing/json_output_parser.py`
- [X] T010 [P] [US1] Implement ItemIdCitationFormatter: scan answer text for `\[ei_[0-9a-f]{16}\]` markers, resolve each against `citation_map` by direct dict lookup, return deduplicated first-appearance-ordered `list[CitationReference]` — `src/core/answer_generation/citation/item_id_formatter.py`
- [X] T011 [P] [US1] Implement NoOpGroundingChecker stub (always returns `[]`); mark file for replacement in Phase 6 — `src/core/answer_generation/grounding/entity_tag_checker.py`
- [X] T012 [US1] Implement AnswerGenerationPipeline with all 8 stages: (1) schema version gate via `_validate_context_version`, (2) no-answer guard, (3) prompt composition, (4) conflict-disclosure injection into `ComposedPrompt.system_message` when `context.conflicts` non-empty, (5) `llm.generate_text_async` call, (6) output parsing, (7) citation formatting, (8) grounding check; structured logging at entry and exit with `plan_id`, `context_id`, provider, token usage, `no_answer`, grounding flag count — `src/core/answer_generation/pipeline.py`
- [X] T013 [US1] Implement AnswerGenerationRegistry: wire DefaultPromptComposer, JsonOutputParser, ItemIdCitationFormatter, NoOpGroundingChecker, resolve config, instantiate and return AnswerGenerationPipeline — `src/core/answer_generation/registry.py`

### Tests for User Story 1

- [X] T014 [P] [US1] Write test_models.py: validate AnswerResult invariants (non-empty answer, citations empty when no_answer=True, schema_version fixed), CitationReference, GroundingFlag construction — `tests/unit/core/answer_generation/test_models.py`
- [X] T015 [P] [US1] Write test_composer.py: verify block ordering preserved, item_id markers embedded, capability modules sorted by priority, system instructions present — `tests/unit/core/answer_generation/test_composer.py`
- [X] T016 [P] [US1] Write test_output_parser.py: JSON parse success, JSON parse failure fallback, empty response → empty string signal, AnswerGenerationError on completely unparseable response — `tests/unit/core/answer_generation/test_output_parser.py`
- [X] T017 [P] [US1] Write test_citation_formatter.py: resolved citations in first-appearance order, unknown markers omitted, duplicate markers deduplicated, empty answer → empty citation list — `tests/unit/core/answer_generation/test_citation_formatter.py`
- [X] T018 [US1] Write test_pipeline.py: happy-path scenario (2-block Context → AnswerResult with citations), schema version mismatch raises SchemaVersionError, mock LLM asserts `generate_text_async` called once — `tests/unit/core/answer_generation/test_pipeline.py`
- [X] T019 [US1] Write integration test Scenarios 1+2 from quickstart.md (valid context → cited answer; citation count matches marker count) with mock LLM — `tests/integration/test_answer_generation_e2e.py`

**Checkpoint**: US1 fully functional — `pytest tests/unit/core/answer_generation/ tests/integration/test_answer_generation_e2e.py` green on happy path.

---

## Phase 4: User Story 3 — No-Answer for Insufficient Context (Priority: P2)

**Goal**: Empty `Context.ordered_blocks` returns an explicit no-answer `AnswerResult`
and the LLM is never called.

**Independent Test**:
```bash
pytest tests/unit/core/answer_generation/test_pipeline.py -k "no_answer" -v
pytest tests/integration/test_answer_generation_e2e.py::test_no_answer_empty_context -v
```

- [X] T020 [US3] Extend test_pipeline.py with no-answer scenarios: empty `ordered_blocks` → `no_answer=True`, `citations=[]`, `answer == config.no_answer_message`, mock LLM `generate_text_async` call count = 0 — `tests/unit/core/answer_generation/test_pipeline.py`
- [X] T021 [US3] Extend integration test with Scenario 4 from quickstart.md (empty Context e2e; LLM mock assert not called) — `tests/integration/test_answer_generation_e2e.py`

**Checkpoint**: US3 validated — no-answer guard fires reliably without LLM call.

---

## Phase 5: User Story 2 — Conflict Disclosure in Answer (Priority: P2)

**Goal**: When `Context.conflicts` is non-empty the generated answer explicitly
discloses the disagreement; `AnswerResult.conflicts_disclosed` is `True`.

**Independent Test**:
```bash
pytest tests/unit/core/answer_generation/test_pipeline.py -k "conflict" -v
pytest tests/integration/test_answer_generation_e2e.py::test_conflict_disclosure -v
```

- [X] T022 [US2] Extend test_pipeline.py with conflict-disclosure scenarios: ConflictGroup in context → `conflicts_disclosed=True`; prompt system_message contains conflict header; empty conflicts → `conflicts_disclosed=False` — `tests/unit/core/answer_generation/test_pipeline.py`
- [X] T023 [US2] Extend test_composer.py with conflict-aware prompt-assembly assertions: verify `ComposedPrompt.has_conflict_disclosure` is set correctly by the pipeline stage — `tests/unit/core/answer_generation/test_composer.py`
- [X] T024 [US2] Extend integration test with Scenario 3 from quickstart.md (conflict-context → `conflicts_disclosed=True`, answer contains disclosure language) — `tests/integration/test_answer_generation_e2e.py`

**Checkpoint**: US2 validated — conflict disclosure is present in 100% of conflict-context runs.

---

## Phase 6: User Story 4 — Grounding Flag for Out-of-Context Claims (Priority: P3)

**Goal**: An LLM answer referencing an entity absent from `Context` emits a
`GroundingFlag`; the answer is still returned.

**Independent Test**:
```bash
pytest tests/unit/core/answer_generation/test_grounding_checker.py -v
pytest tests/unit/core/answer_generation/test_pipeline.py -k "grounding" -v
pytest tests/integration/test_answer_generation_e2e.py::test_grounding_flag -v
```

- [X] T025 [US4] Replace NoOpGroundingChecker stub with real EntityTagGroundingChecker: build `context_vocabulary` from all `ContextBlock.text` values (lowercase); scan answer text for title-cased two-or-more-word sequences absent from vocabulary; emit `GroundingFlag(entity=..., claim=..., reason="entity_not_in_context")` for each; fail-open on internal errors — `src/core/answer_generation/grounding/entity_tag_checker.py`
- [X] T026 [P] [US4] Write test_grounding_checker.py: entity in context → empty flags; entity absent from context → flag emitted; multiple ungrounded entities → multiple flags; internal error → empty list (fail-open); runtime sub-millisecond assertion — `tests/unit/core/answer_generation/test_grounding_checker.py`
- [X] T027 [US4] Update AnswerGenerationRegistry to wire EntityTagGroundingChecker (replacing stub) and respect `config.grounding_check_enabled` toggle — `src/core/answer_generation/registry.py`
- [X] T028 [US4] Extend test_pipeline.py with grounding scenarios: mock LLM emits ungrounded entity → `grounding_flags` non-empty, `answer` still returned; `grounding_check_enabled=False` → `grounding_flags=[]` — `tests/unit/core/answer_generation/test_pipeline.py`
- [X] T029 [US4] Extend integration test with Scenario 6 from quickstart.md (mock LLM introduces entity not in context → flag present, answer returned) — `tests/integration/test_answer_generation_e2e.py`

**Checkpoint**: All four user stories independently validated — full pipeline green.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Constitution compliance, domain packs, observability, and final validation.

- [X] T030 [P] Add domain-specific `system_prompt_template` and `capability_modules` entries to pharmacy and legal field-pack YAML files — `src/fields/pharmacy/answer_generation.yaml`, `src/fields/legal/answer_generation.yaml`
- [X] T031 [P] Extend Prometheus metrics with four new counters/histograms: `answer_generation_duration_seconds`, `citation_resolution_total`, `no_answer_total`, `grounding_flag_total` — `src/utils/metrics.py`
- [X] T032 [P] Add structured-logging assertions to test_pipeline.py: verify log records include `plan_id`, `context_id`, provider name, `no_answer`, grounding flag count at pipeline entry and exit — `tests/unit/core/answer_generation/test_pipeline.py`
- [X] T033 Validate provider-swap scenario (Scenario 5 from quickstart.md): run pipeline with a second mock provider; assert `AnswerResult` shape is identical and pipeline code is unchanged — `tests/integration/test_answer_generation_e2e.py`
- [X] T034 Run all quickstart.md validation scenarios (1–6) against full test suite; confirm `pytest tests/unit/core/answer_generation/ tests/integration/test_answer_generation_e2e.py` exits 0

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user story phases**.
- **Phase 3 (US1, P1)**: Depends on Phase 2. First user story — MVP.
- **Phase 4 (US3, P2)**: Depends on Phase 3 (pipeline.py must exist).
- **Phase 5 (US2, P2)**: Depends on Phase 3. Can run concurrently with Phase 4.
- **Phase 6 (US4, P3)**: Depends on Phase 3.
- **Phase 7 (Polish)**: Depends on Phase 6.

### User Story Dependencies

| Story | Depends on | Can run concurrently with |
|-------|-----------|--------------------------|
| US1 (P1) | Phase 2 complete | — |
| US3 (P2) | Phase 3 complete | US2 |
| US2 (P2) | Phase 3 complete | US3 |
| US4 (P3) | Phase 3 complete | US2, US3 |

### Within Each Phase

- [P]-marked tasks → launch together (different files, no shared state).
- Non-[P] tasks → wait for their listed dependencies within the phase.
- Tests within a story → can run in parallel once source files exist.

---

## Parallel Opportunities

### Phase 2 (Foundational) — run T003–T005 together

```
T003  models.py       ─┐
T004  errors.py        ├─ run in parallel (independent files)
T005  config.py       ─┘
T006  interfaces.py   ← wait for T003, T005
T007  conftest.py     ← parallel with T003–T005
```

### Phase 3 (US1) — run stage implementations together

```
T008  DefaultPromptComposer    ─┐
T009  JsonOutputParser          │
T010  ItemIdCitationFormatter   ├─ run in parallel (independent files)
T011  NoOpGroundingChecker     ─┘
T012  pipeline.py              ← wait for T008–T011
T013  registry.py              ← wait for T012

T014  test_models.py     ─┐
T015  test_composer.py    │
T016  test_output_parser  ├─ run in parallel (independent test files)
T017  test_citation_fmt  ─┘
T018  test_pipeline.py    ← wait for T012, T014–T017
T019  e2e test            ← wait for T013, T018
```

### Phase 5+6 — US2 and US4 in parallel after US1

```
Phase 4 (US3):  T020, T021
Phase 5 (US2):  T022, T023, T024   ─ all can run concurrently with Phase 4
Phase 6 (US4):  T025→T026+T027→T028→T029
```

---

## Implementation Strategy

### MVP (User Story 1 Only) — ~18 tasks

1. Complete Phase 1 + Phase 2 (T001–T007)
2. Complete Phase 3 US1 (T008–T019)
3. **Validate**: `pytest tests/unit/core/answer_generation/ tests/integration/test_answer_generation_e2e.py -k "not conflict and not no_answer and not grounding"`
4. The pipeline already handles no-answer and conflict paths structurally — only the dedicated test coverage is deferred.

### Full Delivery

1. MVP → Phase 4 (US3) → Phase 5 (US2) → Phase 6 (US4) → Phase 7 (Polish)
2. Each phase is independently deployable and testable.
3. Phase 5 and 6 can proceed in parallel after Phase 3.

### Parallel Team Strategy

- **Developer A**: T003–T006 (foundational) → T008, T010 (composer, citation formatter)
- **Developer B**: T007 (conftest) → T009, T011 (parser, grounding stub) → T014–T017 (tests)
- After T012 (pipeline): Developer A → Phase 4+5 · Developer B → Phase 6

---

## Notes

- [P] = different source files, no in-flight dependency — safe to parallelize.
- [US#] maps directly to user story priority in spec.md.
- Do not call `LLMInterface.generate_text` directly — always use `generate_text_async`.
- `ComposedPrompt` is frozen; conflict-disclosure injection uses `model_copy(update={...})` to produce a new instance.
- `EntityTagGroundingChecker` must fail-open (catch all exceptions → return `[]`) per `IGroundingChecker` contract.
- Commit after each phase checkpoint; validate independently before starting the next phase.
