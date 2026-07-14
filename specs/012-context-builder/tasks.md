# Tasks: Context Builder (spec 012)

**Input**: Design documents from `specs/012-context-builder/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Required per constitution (Principle VII). Test tasks are included for every user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths are included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the package skeleton. No logic yet — only directories, `__init__.py` files, and field-pack YAML stubs.

- [X] T001 Create `src/core/context_builder/` package tree: sub-dirs `budget/`, `compression/`, `conflict/`, `dedup/`, `stitching/` each with `__init__.py`; add top-level `__init__.py`
- [X] T002 [P] Create `tests/unit/core/context_builder/__init__.py` and `tests/unit/core/context_builder/conftest.py` with shared `EvidencePack`/`EvidenceItem` builder helpers (`make_item`, `make_pack`, `build_synthetic_pack`)
- [X] T003 [P] Create `src/fields/generic/context_builder.yaml` with generic baseline values from data-model.md Config File Layout section
- [X] T004 [P] Create `src/fields/pharmacy/context_builder.yaml` with `total_context_window: 16000` override and all other keys inherited from generic
- [X] T005 [P] Create `src/fields/legal/context_builder.yaml` with `compression_strategy: heuristic` and `compressibility_threshold: 0.65` override

**Checkpoint**: Package tree and config stubs exist; `import core.context_builder` succeeds.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain types, config, errors, and interfaces that every user-story phase depends on. No user story implementation can begin until this phase is complete.

- [X] T006 Implement `src/core/context_builder/errors.py`: `ContextBuildError(Exception)` base; subclasses `EvidencePackVersionError`, `EmptyBudgetError`, `CitationIntegrityError` — all carry a `detail: str` field
- [X] T007 [P] Implement `src/core/context_builder/models.py`: Pydantic v2 models `ContextBlock`, `ConflictGroup`, `ContextMetadata`, `Context` with all fields and invariant validators from data-model.md (including the `item_ids == citation_map keys` validator and `token_count == sum(blocks)` validator)
- [X] T008 [P] Implement `src/core/context_builder/config.py`: `BudgetReservations` and `ContextBuilderConfig` Pydantic models; `available_budget` computed property; `load_config_from_yaml(path)` and `merge_config(base, override)` helpers following the pattern in `src/core/evidence_orchestrator/config.py`
- [X] T009 Implement `src/core/context_builder/interfaces.py`: abstract base classes `ITokenBudgetAllocator` (sync `allocate(config) → int`), `IContextCompressor` (async `compress(item, target_tokens, token_counter) → tuple[str, int]`), `IConflictDetector` (async `detect(items, config) → list[ConflictGroup]`), `IContextStitcher` (async `stitch(items, token_counter) → list[ContextBlock]`); import `ITokenCounter` from `core.evidence_orchestrator.interfaces` (do not redefine)
- [X] T010 [P] Write `tests/unit/core/context_builder/test_models.py`: invariant tests for `Context` — citation completeness validator raises `ValidationError` on mismatch, `token_count` sum invariant, empty-pack construction, `ConflictGroup.resolution` field accepts `None` and `"budget_drop"`

**Checkpoint**: `pytest tests/unit/core/context_builder/test_models.py` passes. `ContextBuilderConfig.available_budget` returns correct value. All imports resolve.

---

## Phase 3: User Story 1 — Budget-Constrained Context Assembly (Priority: P1) 🎯 MVP

**Goal**: Given an `EvidencePack` exceeding the token budget, emit a `Context` within budget, retaining the highest-ranked items (compressing or dropping high-compressibility items first), with zero broken citations.

**Independent Test**: `pytest tests/unit/core/context_builder/test_budget_allocator.py tests/unit/core/context_builder/test_selector.py tests/unit/core/context_builder/test_heuristic_compressor.py` all pass. `pytest tests/unit/core/context_builder/test_pipeline.py -k us1` passes.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Write `tests/unit/core/context_builder/test_budget_allocator.py`: `DefaultTokenBudgetAllocator.allocate()` returns `window − system − question − output`; returns 0 when reservations ≥ window; never returns negative
- [X] T012 [P] [US1] Write `tests/unit/core/context_builder/test_heuristic_compressor.py`: compressed text ≤ target tokens (within one-sentence tolerance); non-empty output when input is non-empty; `target_tokens=0` → `("", 0)`; sentence-boundary split preserves complete sentences; hard-truncation fallback when no boundary found
- [X] T013 [P] [US1] Write `tests/unit/core/context_builder/test_selector.py`: items selected in descending relevance order; high-compressibility items compressed before lower-scored items are dropped; all included items have citations; `metadata.items_dropped + metadata.items_included == len(pack.items)`; all-items-fit scenario includes everything uncompressed

### Implementation for User Story 1

- [X] T014 [US1] Implement `src/core/context_builder/budget/default_allocator.py`: `DefaultTokenBudgetAllocator(ITokenBudgetAllocator)` — sync `allocate(config) → int`; returns `max(0, config.total_context_window − reservations_sum)`
- [X] T015 [US1] Implement `src/core/context_builder/compression/heuristic_compressor.py`: `HeuristicTruncationCompressor(IContextCompressor)` — async `compress(item, target_tokens, token_counter)`; split on `(?<=[.?!])\s+`; greedy sentence append; hard-char fallback at `target_tokens * 4` chars; never raises (returns truncated text on any failure)
- [X] T016 [US1] Implement the selection helper in `src/core/context_builder/pipeline.py` (private `_select_under_budget` coroutine): iterate `pack.items` (already ranked descending); for each item, if uncompressed token count fits → include; if `compressibility_score > threshold` and compression is enabled → try `IContextCompressor.compress()`; if compressed fits → include compressed; else drop; track `compressed: bool` alongside each selected `EvidenceItem`; stop when budget is exhausted
- [X] T017 [US1] Implement `src/core/context_builder/pipeline.py` `ContextBuilderPipeline` class skeleton: `__init__` accepting all four interface instances + `ITokenCounter`; async `build(pack, config) → Context`; validate `pack.schema_version` major version → raise `EvidencePackVersionError` on mismatch; call `ITokenBudgetAllocator.allocate(config)` → raise `EmptyBudgetError` when 0; call `_select_under_budget`; assemble a partial `Context` (no conflict, no stitch, no final dedup yet — those are added in later phases); validate citation integrity; return `Context`
- [X] T018 [US1] Implement `src/core/context_builder/registry.py`: `ContextBuilderRegistry.build(config) → ContextBuilderPipeline` factory; selects `HeuristicTruncationCompressor` when `compression_strategy == "heuristic"`; wires `DefaultTokenBudgetAllocator`; wires token counter from `config.token_counter` (`"character"` → `CharacterApproximationTokenCounter`, `"tiktoken"` → `TiktokenTokenCounter`); uses stub no-op implementations for conflict detector and stitcher until those phases are complete
- [X] T019 [US1] Add structured logging to `pipeline.py` `build()`: log `pack_id`, `plan_id`, `items_in`, budget at entry; log `items_selected`, `items_compressed`, `items_dropped`, elapsed ms after selection; emit `CONTEXT_HARD_DROP` structured event when any item is dropped

**Checkpoint**: Running `pytest tests/unit/core/context_builder/test_budget_allocator.py tests/unit/core/context_builder/test_selector.py tests/unit/core/context_builder/test_heuristic_compressor.py` passes. A synthetic 20-item 12 000-token pack with 6 300-token budget produces `ctx.token_count ≤ 6300` and `len(ctx.ordered_blocks) == len(ctx.citation_map)`.

---

## Phase 4: User Story 2 — Conflict Detection and Disclosure (Priority: P2)

**Goal**: Two `EvidenceItem` objects that reference the same entity with differing numeric or categorical values produce a `ConflictGroup` in `Context.conflicts`. Answer Generation receives the conflict list without losing either item.

**Independent Test**: `pytest tests/unit/core/context_builder/test_conflict_detector.py` passes. Conflict group correctly identifies both item ids; non-conflicting packs return `[]`.

### Tests for User Story 2 ⚠️

- [X] T020 [P] [US2] Write `tests/unit/core/context_builder/test_conflict_detector.py`: two items sharing one entity_tag with different numeric values in text → one `ConflictGroup`; no shared entity_tag → empty `[]`; three items all sharing the same tag and value conflict → single merged group (not three pairs); detector failure (exception in implementation) → returns `[]`, does not raise; `ConflictGroup.item_ids` are all present in input list

### Implementation for User Story 2

- [X] T021 [US2] Implement `src/core/context_builder/conflict/entity_tag_detector.py`: `EntityTagConflictDetector(IConflictDetector)` — async `detect(items, config)`; build inverted index `{entity_tag → list[EvidenceItem]}`; for each tag group with ≥ 2 items, extract numeric tokens within 100-char window of entity_tag mention in `item.text` using regex `r'\b\d+(?:\.\d+)?\b'`; if extracted values differ across items → emit `ConflictGroup(entity_tag=tag, attribute=f"{tag}:numeric", item_ids=[...], resolution=None)`; categorical pass: detect mutually exclusive tokens (e.g., `"daily"` vs `"weekly"`) → `attribute=f"{tag}:categorical"`; merge groups by `(entity_tag, attribute)`; catch all exceptions → log warning → return `[]`
- [X] T022 [US2] Wire `EntityTagConflictDetector` into `ContextBuilderRegistry.build()` replacing the no-op stub; update `pipeline.py` `build()` to call `IConflictDetector.detect(selected_items, config)` after selection and assign result to `Context.conflicts`; set `ConflictGroup.resolution = "budget_drop"` for any `item_id` in a conflict group that was not included in `ordered_blocks`
- [X] T023 [US2] Update `pipeline.py` structured logging: log `conflicts_detected` count after conflict detection stage

**Checkpoint**: `pytest tests/unit/core/context_builder/test_conflict_detector.py` passes. A pack with two items sharing `entity_tags=["metformin"]` and different dosage values in text produces `len(ctx.conflicts) == 1`.

---

## Phase 5: User Story 3 — Coherent Document-Structure Ordering (Priority: P2)

**Goal**: Surviving items are ordered by `(document_id, section_path list, -relevance_score)` and converted to `ContextBlock` objects. Items from the same document appear consecutively in heading order.

**Independent Test**: `pytest tests/unit/core/context_builder/test_stitcher.py` passes. Items from two documents produce consecutive document blocks; items within same document are ordered by `section_path`.

### Tests for User Story 3 ⚠️

- [X] T024 [P] [US3] Write `tests/unit/core/context_builder/test_stitcher.py`: three items from two docs → doc blocks are contiguous; within same doc, `["Introduction"]` < `["Results"]` in output order; items with `section_path=[]` sort after items with a path within same doc; items with no `document_id` appear last; `len(result) == len(input)` invariant; `section_path` on block equals `"/".join(item.section_path)` or `None`; `compressed` flag passed through correctly

### Implementation for User Story 3

- [X] T025 [US3] Implement `src/core/context_builder/stitching/section_path_stitcher.py`: `SectionPathStitcher(IContextStitcher)` — async `stitch(items, token_counter) → list[ContextBlock]`; sort key `(doc_id_sort_key, section_path_list, -relevance_score)` where `doc_id_sort_key = ("" if doc_id else "\xff", doc_id)` (empty doc_id last); `section_path_list = item.section_path if item.section_path else ["\xff"]` (empty path after non-empty within same doc); construct `ContextBlock` per item with `section_path="/".join(item.section_path) or None`; `token_count=token_counter.count_tokens(item.text)`; `compressed` passed from caller
- [X] T026 [US3] Wire `SectionPathStitcher` into `ContextBuilderRegistry.build()` replacing the no-op stub; update `pipeline.py` `build()` to call `IContextStitcher.stitch(selected_items_with_compressed_flag, token_counter)` after conflict detection; replace the preliminary `ordered_blocks` with the stitcher output; recompute `Context.token_count` from stitched blocks

**Checkpoint**: `pytest tests/unit/core/context_builder/test_stitcher.py` passes. A mixed-document pack produces document-grouped, section-ordered blocks regardless of input order or relevance ranking.

---

## Phase 6: User Story 4 — Final-Pass Duplicate Safety Net (Priority: P3)

**Goal**: Near-duplicate items that survived Evidence Orchestrator (with its higher embedding-based threshold) are removed by char 3-gram Jaccard similarity before assembly. Lower-ranked duplicate is dropped; higher-ranked is retained.

**Independent Test**: `pytest tests/unit/core/context_builder/test_final_dedup.py` passes. Two items above threshold → lower-ranked dropped. Two items below threshold → both retained.

### Tests for User Story 4 ⚠️

- [X] T027 [P] [US4] Write `tests/unit/core/context_builder/test_final_dedup.py`: two items with Jaccard similarity > 0.85 → lower-ranked item absent from output; two items with similarity < 0.85 → both retained; citation map does not contain dropped item id; `final_dedup_enabled=False` → all items pass through unchanged; more than `final_dedup_max_pairs` comparisons → capped and remainder pass through

### Implementation for User Story 4

- [X] T028 [US4] Implement `src/core/context_builder/dedup/text_similarity_dedup.py`: `FinalPassDeduplicator` — sync helper (called inside `async def`); accepts `items: list[EvidenceItem]` + `config: ContextBuilderConfig`; for each pair `(i, j)` where `i < j`, compute `jaccard_similarity(char_ngrams(item_i.text), char_ngrams(item_j.text))` importing from `core.evidence_orchestrator.text_similarity`; if similarity ≥ `final_dedup_similarity_threshold` → mark lower `relevance_score` item for removal; cap total comparisons at `final_dedup_max_pairs`; return filtered `list[EvidenceItem]`
- [X] T029 [US4] Integrate `FinalPassDeduplicator` into `pipeline.py` `build()`: call after `_select_under_budget` and before conflict detection (order: select → final_dedup → conflict → stitch → assemble); update `metadata.items_dropped` to include final-dedup drops; log `final_dedup_removed` count in structured log entry

**Checkpoint**: `pytest tests/unit/core/context_builder/test_final_dedup.py` passes. Two nearly-identical items in a pack produce one block in `Context.ordered_blocks`.

---

## Phase 7: Full Pipeline Assembly & Integration Tests

**Purpose**: Complete the pipeline, verify all stages interact correctly, run end-to-end integration test, and validate all six quickstart scenarios.

- [X] T030 Write `tests/unit/core/context_builder/test_pipeline.py`: full pipeline unit test using mock implementations of all four interfaces; verify stage ordering (allocate → select → dedup → conflict → stitch → assemble); verify `EvidencePackVersionError` raised on major-version mismatch; verify `EmptyBudgetError` raised when budget = 0; verify timeout flag set when `asyncio.wait_for` times out; verify citation integrity validator fires on mismatched citation map; performance benchmark fixture (`-k bench`) asserts median run ≤ 150 ms on 50-item pack using `time.perf_counter` (no live LLM, heuristic compressor)
- [X] T031 [P] Write `tests/integration/test_context_builder_e2e.py`: end-to-end scenarios matching quickstart.md — Scenario 1 (budget compliance), Scenario 2 (compressibility ordering), Scenario 3 (conflict detection), Scenario 4 (document ordering), Scenario 5 (zero broken citations across all scenarios), Scenario 6 (empty pack); use `ContextBuilderRegistry.build(config)` with real implementations; no live LLM; heuristic compressor only
- [X] T032 Finalize `pipeline.py` `build()`: add `asyncio.wait_for` wrapper around the inner pipeline coroutine using `config.timeout_seconds`; on `asyncio.TimeoutError` return partial `Context` with `metadata.timeout=True` and whatever blocks were assembled before timeout; add `CitationIntegrityError` assertion before returning (raises only in non-timeout path)
- [X] T033 [P] Verify `ContextBuilderRegistry.build()` covers all `compression_strategy` values; add guard that raises `ValueError` on unknown strategy string; add guard for unknown `token_counter` string

**Checkpoint**: `pytest tests/unit/core/context_builder/ tests/integration/test_context_builder_e2e.py -v` — all pass. Performance benchmark ≤ 150 ms p95 on 50-item pack.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T034 [P] Implement `src/core/context_builder/compression/llm_compressor.py`: `LLMContextCompressor(IContextCompressor)` — async `compress(item, target_tokens, token_counter)`; calls `LLMProviderFactory` to summarize `item.text`; activated via `compression_strategy: "llm"` in config; wire into `ContextBuilderRegistry`; guarded by import-time check that provider is available
- [X] T035 [P] Add `context_builder` namespace to field-pack loading in `src/services/FieldRegistry.py` (or equivalent field resolution entry point in `src/core/field_resolution.py`) so domain packs are resolved via `generic < domain < project` precedence matching the pattern used by `evidence_orchestrator`
- [X] T036 [P] Add Prometheus metric stubs in `src/utils/metrics.py`: `context_builder_pipeline_duration_seconds` histogram; `context_builder_items_dropped_total` counter; `context_builder_conflicts_detected_total` counter — following existing metric registration pattern
- [X] T037 Run `ruff` linter across `src/core/context_builder/` and `tests/unit/core/context_builder/`; fix all lint errors
- [X] T038 Run full quickstart.md validation manually: all six scenarios produce expected outcomes; record results as comments in `quickstart.md`

**Checkpoint**: Lint clean. All quickstart scenarios verified. Optional LLM compressor wired and registry tested.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — **blocks all user story phases**
- **Phase 3 (US1)**: Depends on Phase 2 — is the MVP; deliver and validate before starting Phase 4+
- **Phase 4 (US2)**: Depends on Phase 2; can start concurrently with Phase 3 if staffed (different files)
- **Phase 5 (US3)**: Depends on Phase 2; can start concurrently with Phase 3/4 (different files)
- **Phase 6 (US4)**: Depends on Phase 2; can start concurrently after Phase 2 (different files)
- **Phase 7 (Integration)**: Depends on Phases 3–6 all complete
- **Phase 8 (Polish)**: Depends on Phase 7

### User Story Dependencies

- **US1 (P1)**: Only requires Phase 2 complete — **no dependency on US2/US3/US4**
- **US2 (P2)**: Only requires Phase 2 complete — integrates with US1's pipeline after Phase 3 done
- **US3 (P2)**: Only requires Phase 2 complete — integrates with US1's pipeline after Phase 3 done
- **US4 (P3)**: Only requires Phase 2 complete — integrates with US1's pipeline after Phase 3 done

### Within Each User Story Phase

- Test tasks `[P]` can all start simultaneously (different files)
- Implementation tasks depend on tests existing (write tests first)
- `pipeline.py` update task comes after the stage implementation task
- Registry wiring comes last within each phase

### Parallel Opportunities

All `[P]`-marked tasks within the same phase can be executed concurrently. Key parallelism:

- T002, T003, T004, T005 — all Phase 1 setup (different files)
- T007, T008, T010 — foundational models, config, and tests (different files)
- T011, T012, T013 — all US1 test files (different files)
- T020, T024, T027 — test files for US2, US3, US4 can all be written in parallel
- T034, T035, T036 — polish tasks are entirely independent

---

## Parallel Example: User Story 1

```bash
# Step 1 — write all US1 tests simultaneously (they share conftest but write to different files):
Task: T011 "Write tests/unit/core/context_builder/test_budget_allocator.py"
Task: T012 "Write tests/unit/core/context_builder/test_heuristic_compressor.py"
Task: T013 "Write tests/unit/core/context_builder/test_selector.py"

# Step 2 — implement (after tests exist and fail):
Task: T014 "Implement budget/default_allocator.py"
Task: T015 "Implement compression/heuristic_compressor.py"
# T016, T017, T018, T019 are sequential (pipeline.py and registry.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete **Phase 1**: Setup (T001–T005)
2. Complete **Phase 2**: Foundational (T006–T010) — **CRITICAL BLOCKER**
3. Complete **Phase 3**: US1 Budget Assembly (T011–T019)
4. **STOP and VALIDATE**: `pytest tests/unit/core/context_builder/` passes; 20-item over-budget pack → `ctx.token_count ≤ budget` and `len(ctx.ordered_blocks) == len(ctx.citation_map)`
5. **Deploy/demo if ready** — pipeline is usable end-to-end for the core case

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 (T011–T019) → budget-compliant assembly with citation integrity → **MVP**
3. US2 (T020–T023) → conflict detection added → test independently
4. US3 (T024–T026) → structured ordering added → test independently
5. US4 (T027–T029) → final dedup added → test independently
6. Phase 7 (T030–T033) → integration tests and timeout handling
7. Phase 8 (T034–T038) → LLM compressor, metrics, lint

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- **Developer A**: Phase 3 (US1 — core budget assembly + heuristic compressor)
- **Developer B**: Phase 4 + 5 (US2 conflict detection + US3 ordering, write test files first)
- **Developer C**: Phase 6 (US4 final dedup) + Phase 8 polish tasks

Merge order: US1 first (it defines the pipeline skeleton); US2/US3/US4 each add a stage.

---

## Notes

- `[P]` tasks write to different files — safe for concurrent execution
- `[Story]` label maps each task to a specific user story for traceability
- Test tasks MUST be written and confirmed failing before the corresponding implementation task
- `ITokenCounter`, `char_ngrams`, `jaccard_similarity` are **imported** from `core.evidence_orchestrator` — do not duplicate
- `pipeline.py` is modified incrementally across Phases 3–6; each phase adds one stage call
- `registry.py` is updated in each implementation phase to wire the new concrete class
- Commit after each checkpoint to keep main stable
