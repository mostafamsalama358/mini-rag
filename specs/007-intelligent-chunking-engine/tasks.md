# Tasks: Intelligent Chunking Engine

**Input**: Design documents from `specs/007-intelligent-chunking-engine/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Included per constitution Principle VII — required for all changed behavior.

**Organization**: Tasks grouped by user story for independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US6 map to spec.md user stories)
- All paths relative to repo root; source under `src/`, tests under `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the file and directory skeleton so all phases can proceed in parallel.

- [X] T001 Create `src/core/chunking/strategies/` directory with empty `__init__.py` placeholder
- [X] T002 [P] Create test directory tree: `tests/unit/chunking/`, `tests/integration/chunking/`, `tests/integration/benchmarks/`, `tests/fixtures/chunking/` — each with an empty `__init__.py`
- [X] T003 [P] Create empty placeholder files for all new source modules: `src/core/chunking/models.py`, `src/core/chunking/interfaces.py`, `src/core/chunking/registry.py`, `src/core/chunking/evaluator.py`, `src/core/chunking/builder.py`, `src/core/chunking/validator.py`, `src/core/chunking/strategies/semantic_structural.py`
- [X] T004 Run the existing unit + integration test suite (`cd src && pytest tests/ -q --tb=short`) and record the baseline pass count — this is the regression gate for all subsequent tasks

**Checkpoint**: All new directories and placeholder files exist; baseline test count recorded.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, interfaces, registry, and YAML config that EVERY user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Extend `StructuralElementType = Literal[...]` in `src/core/document_intelligence/model.py` to add `"heading"`, `"code-block"`, `"quote"`, `"figure-placeholder"` and update `CANONICAL_ELEMENT_TYPES` frozenset (FR-004, research R4); keep all six existing types and their validation rules unchanged
- [X] T006 [P] Implement all Pydantic v2 models in `src/core/chunking/models.py`: `SizeBudgetStatus`, `BoundaryCandidate`, `BoundaryFeatures` (11 fields per data-model.md §3), `BoundaryDecision` (4 fields per data-model.md §4), `ChunkLineage`, `StructuralContext`, `ChunkIdentity`, `ChunkRelationships`, `Chunk` (extended, data-model.md §9), `ValidationReport` (data-model.md §10), `ChunkSet` (data-model.md §11), `ChunkingStrategyConfig` (data-model.md §12)
- [X] T007 [P] Implement `ChunkingStrategy` ABC and `BoundaryDecisionPolicy` Protocol in `src/core/chunking/interfaces.py` exactly as specified in `contracts/chunking-strategy-contract.md` and `contracts/boundary-decision-policy-contract.md`
- [X] T008 Implement `src/core/chunking/registry.py` with `register_strategy(name, cls)`, `get_chunking_strategy(name, config) -> ChunkingStrategy`, `register_policy(name, cls)`, `get_boundary_decision_policy(name) -> BoundaryDecisionPolicy`; raise `KeyError` for unknown names (loud failure, no silent fallback)
- [X] T009 [P] Add `strategy: str = "semantic_structural"` and `policy: str = "rule_based"` fields to `ChunkingProfile` in `src/fields/schemas.py`; default values preserve backward-compat for packs that omit the new keys
- [X] T010 [P] Add `strategy: semantic_structural` and `policy: rule_based` to `src/fields/generic/chunking.yaml`, `src/fields/pharmacy/chunking.yaml`, and `src/fields/legal/chunking.yaml` (additive YAML keys only)
- [X] T011 Implement a stub `ChunkValidator` in `src/core/chunking/validator.py` that accepts a `list[Chunk]` and returns a `ValidationReport` with `status="pass"`, empty `failed_rules`, empty `warnings`, empty `validation_messages` — this stub is replaced in US6; it exists so the pipeline can return a `ChunkSet` from T020 onward
- [X] T012 Update `src/core/chunking/__init__.py` to export: `ChunkingStrategy`, `BoundaryDecisionPolicy`, `BoundaryFeatures`, `BoundaryDecision`, `ChunkSet`, `ValidationReport`, `ChunkingStrategyConfig`, `get_chunking_strategy`, `get_boundary_decision_policy`, `register_strategy`, `register_policy`

**Checkpoint**: Foundation ready — `from core.chunking import ChunkSet, get_chunking_strategy` works; YAML packs load without error; all six existing element types still validate correctly.

---

## Phase 3: User Story 1 — Semantic Boundaries over Token Utilization (Priority: P1) 🎯 MVP

**Goal**: Replace `map_elements_to_chunks` with an engine that keeps headings with their content, never splits table rows mid-row, and never merges elements from different sections — regardless of token budget.

**Independent Test**: `cd src && pytest tests/unit/chunking/test_semantic_boundaries.py -v`

### Tests for User Story 1 ⚠️

> Write these tests FIRST and confirm they FAIL before implementing T016–T022.

- [X] T013 [P] [US1] Create `tests/fixtures/chunking/heading_table_sections.py` with `FIXTURE_DOC` DocumentModel containing: heading → 2 paragraphs → table element → 2 table-rows (with `parent_id` pointing to the table) → new heading → paragraph (mirrors quickstart Scenario 1)
- [X] T014 [P] [US1] Write `tests/unit/chunking/test_semantic_boundaries.py` covering: (a) heading not separated from first paragraph, (b) table-rows not merged across parent boundaries, (c) no chunk spans both headings, (d) heading appears in `heading_path` of all chunks produced under it — assert all four fail before implementation

### Implementation for User Story 1

- [X] T015 [US1] Implement `SemanticBoundaryEvaluator.evaluate(candidate: BoundaryCandidate, context: dict) -> BoundaryFeatures` in `src/core/chunking/evaluator.py` computing all 11 signal fields deterministically per research R8 (hierarchy_continuity via parent_id equality, heading_continuity via type inspection, section_continuity via ancestor lookup, structural_compatibility via compatibility groups A/B/C/D, lexical_continuity rule-based, table/list/code/quote integrity checks, layout_continuity via page provenance, size_budget by char count)
- [X] T016 [US1] Implement `RuleBasedBoundaryDecisionPolicy.decide(candidate, features) -> BoundaryDecision` in `src/core/chunking/strategies/semantic_structural.py` applying the 7-level rule precedence from research R1 (structural integrity → section boundary → heading boundary → hierarchy breach → size budget → type incompatibility → layout+lexical → default merge); every decision includes `applied_rule`, non-empty `triggered_features`, and `rationale`
- [X] T017 [US1] Implement `ChunkBuilder` in `src/core/chunking/builder.py` with stateful lifecycle: `open_chunk()`, `append_element(element, merge_decision)`, `close_chunk(split_decision)`, `_emit_chunk() -> Chunk`; include `_OversizedSplitter` helper that splits a single oversized element's text at paragraph → sentence → character boundaries (research R7), recording `applied_rule="oversized_element_fallback"` in lineage; identity and relationships are placeholder stubs at this phase (filled in US3/US4)
- [X] T018 [US1] Implement `SemanticStructuralChunkingStrategy.chunk(document_model, config) -> ChunkSet` in `src/core/chunking/strategies/semantic_structural.py` orchestrating: iterate elements → create BoundaryCandidate for each adjacent pair → SemanticBoundaryEvaluator.evaluate → RuleBasedBoundaryDecisionPolicy.decide → ChunkBuilder → stub ChunkValidator → return ChunkSet; strategy_id = `"semantic_structural"`
- [X] T019 [US1] Register `SemanticStructuralChunkingStrategy` under name `"semantic_structural"` and `RuleBasedBoundaryDecisionPolicy` under name `"rule_based"` in `src/core/chunking/strategies/__init__.py` via `register_strategy` / `register_policy`
- [X] T020 [US1] Replace the `map_elements_to_chunks` call in `src/tasks/file_processing.py` with `strategy.chunk(document_model, config)` using `get_chunking_strategy` from the registry; extract `records = [{"text": c.text, "metadata": c.metadata} for c in chunk_set.chunks]`; log validation report status at task boundary

**Checkpoint**: `pytest tests/unit/chunking/test_semantic_boundaries.py -v` passes; existing integration test suite regression-free.

---

## Phase 4: User Story 2 — Strategy-Based, Swappable Chunking Architecture (Priority: P1)

**Goal**: A new chunking strategy or Boundary Decision Policy can be added and selected via configuration with zero changes to the engine's dispatch logic or any downstream code.

**Independent Test**: `cd src && pytest tests/integration/chunking/test_strategy_swap.py -v`

### Tests for User Story 2 ⚠️

> Write these tests FIRST and confirm they FAIL before implementing T023–T026.

- [X] T021 [P] [US2] Write `tests/integration/chunking/test_strategy_swap.py` with three test functions: `test_default_strategy` (runs SemanticStructural on fixture, verifies ChunkSet shape), `test_passthrough_strategy` (registers + uses a PassthroughStrategy, verifies same metadata key set), `test_downstream_contract_unchanged` (asserts `text` and all backward-compat `metadata` keys identical in both strategies' output)

### Implementation for User Story 2

- [X] T022 [US2] Implement `PassthroughChunkingStrategy` in `tests/integration/chunking/fixtures/passthrough_strategy.py`: emits one chunk per structural element, no merging, minimal BoundaryDecision stubs; register under `"passthrough"` in the test fixture's setup; strategy_id = `"passthrough"`
- [X] T023 [US2] Add a `test_policy_swap` test function to `test_strategy_swap.py`: implements a `FirstAlwaysSplitPolicy` (always returns `split`), registers it via `register_policy`, constructs a strategy with `config.policy="always_split"`, verifies the evaluator and engine dispatch require zero changes (SC-010)
- [X] T024 [US2] Add a `test_yaml_driven_strategy_selection` test to `test_strategy_swap.py`: load a test `chunking.yaml` with `strategy: passthrough`, run `ChunkingProfile.for_extension(".txt")` + strategy factory, verify `PassthroughChunkingStrategy` is selected without touching file_processing.py
- [X] T025 [US2] Add parallel-strategy test to `test_strategy_swap.py`: run both `SemanticStructural` and `Passthrough` on the same fixture in sequence; assert downstream-compatible `records` (text/metadata) differ in content but share all required key names (FR-031/FR-032, SC-004)

**Checkpoint**: `pytest tests/integration/chunking/test_strategy_swap.py -v` passes; adding a new strategy requires only implementing `ChunkingStrategy` + `register_strategy()`.

---

## Phase 5: User Story 3 — Hierarchical, Relationship-Aware Chunk Output (Priority: P1)

**Goal**: Every chunk carries valid parent/child hierarchy and previous/next adjacency links, enabling context-aware retrieval expansion.

**Independent Test**: `cd src && pytest tests/unit/chunking/test_relationships.py -v`

### Tests for User Story 3 ⚠️

> Write these tests FIRST and confirm they FAIL before implementing T028–T032.

- [X] T026 [P] [US3] Write `tests/unit/chunking/test_relationships.py` covering: (a) every `child_chunk_id` resolves to an actual chunk in the set, (b) following `next_chunk_id` from chunk_position=0 visits every chunk exactly once in order, (c) no dangling `parent_chunk_id`/`previous_chunk_id`/`next_chunk_id`, (d) section-level chunk has non-empty `child_chunk_ids`

### Implementation for User Story 3

- [X] T027 [US3] Extend `ChunkBuilder` in `src/core/chunking/builder.py` to track `_heading_stack: list[str]` (stack of section/heading element ids) and `_current_section_chunk_id: str | None`; update heading_stack whenever a `heading` or `section` element is opened; assign `parent_chunk_id = _current_section_chunk_id` to all non-section chunks emitted while that section is active (research R9)
- [X] T028 [US3] Extend `ChunkBuilder`: add post-close pass that iterates the finalized ordered chunk list once, assigning `previous_chunk_id` and `next_chunk_id` to each chunk by index; this pass runs after all chunks are closed but before `ChunkSet` is assembled (research R9)
- [X] T029 [US3] Extend `ChunkBuilder`: after the prev/next pass, iterate section-level chunks and populate `child_chunk_ids` by collecting all chunk ids whose `parent_chunk_id` matches the section chunk's identity
- [X] T030 [US3] Promote referential integrity to the stub `ChunkValidator` in `src/core/chunking/validator.py`: check that every non-null relationship id (parent, previous, next, child) appears in the emitted chunk set; add to `failed_rules` if not (pre-empts the full US6 implementation for this one rule, since relationships are live from this phase)

**Checkpoint**: `pytest tests/unit/chunking/test_relationships.py -v` passes; `referential_integrity` validation rule active.

---

## Phase 6: User Story 4 — Stable Identity, Lineage, and Reproducibility (Priority: P2)

**Goal**: Re-chunking the same unchanged DocumentModel with the same configuration always produces identical chunk IDs, text, relationships, and lineage; every chunk's lineage names its source elements and the rule that produced it.

**Independent Test**: `cd src && pytest tests/unit/chunking/test_determinism.py -v`

### Tests for User Story 4 ⚠️

> Write these tests FIRST and confirm they FAIL before implementing T033–T036.

- [X] T031 [P] [US4] Write `tests/unit/chunking/test_determinism.py` covering: (a) two runs on same fixture + config produce identical `chunk_id`, `text`, `relationships`, and `lineage` fields, (b) BoundaryDecision replay: extract (features, decision) from run 1, replay through `RuleBasedBoundaryDecisionPolicy.decide`, assert reproduced decision equals original (SC-015), (c) assert no `BoundaryDecision` contains a numeric confidence/probability field (SC-016)

### Implementation for User Story 4

- [X] T032 [US4] Implement `ChunkIdentity` computation in `src/core/chunking/builder.py`: after closing a chunk, compute `chunk_id = "ck_" + SHA256(f"{asset_id}|{','.join(sorted(source_element_ids))}|{strategy_id}|{config_hash}")[:16]` where `config_hash = SHA256(json.dumps(config.model_dump(), sort_keys=True))[:8]`; assign `ChunkIdentity` only after chunk is closed (FR-047, research R2)
- [X] T033 [US4] Implement `ChunkLineage` recording in `src/core/chunking/builder.py`: capture `applied_rule`, `triggered_features`, and `rationale` from the closing `BoundaryDecision` (or from the `_OversizedSplitter` for oversized fragments) into each emitted chunk's `lineage`; persist `lineage` dict as `chunk.metadata["lineage"]`
- [X] T034 [US4] Populate new additive metadata keys from identity, relationships, and structural context into `chunk.metadata` during `_emit_chunk()`: `chunk_id`, `parent_chunk_id`, `previous_chunk_id`, `next_chunk_id`, `heading_path`, `chunk_position`, `lineage` (contracts/chunk-output-contract.md §New additive keys)
- [X] T035 [US4] Add `config_hash` computation helper function in `src/core/chunking/registry.py` or `src/core/chunking/models.py` to ensure `ChunkingStrategyConfig` produces a stable, deterministic fingerprint (sort_keys=True on model_dump, encode to UTF-8 before SHA256)

**Checkpoint**: `pytest tests/unit/chunking/test_determinism.py -v` passes; chunk_id values are stable across runs.

---

## Phase 7: User Story 5 — Extended Structural Awareness: Code, Quotes, Figures, Headings (Priority: P2)

**Goal**: `code-block`, `quote`, and `figure-placeholder` are treated as atomic, addressable semantic units — never merged with unrelated paragraph text.

**Independent Test**: `cd src && pytest tests/unit/chunking/test_extended_types.py -v`

### Tests for User Story 5 ⚠️

> Write these tests FIRST and confirm they FAIL before implementing T038–T041.

- [X] T036 [P] [US5] Create `tests/fixtures/chunking/extended_types.py` with `EXTENDED_DOC` DocumentModel containing: paragraph → code-block → paragraph → quote → figure-placeholder (mirrors quickstart Scenario 5 fixture)
- [X] T037 [P] [US5] Write `tests/unit/chunking/test_extended_types.py` covering: (a) code-block is not merged with adjacent paragraphs, (b) figure-placeholder produces its own non-empty chunk (even with minimal text), (c) quote is not merged with non-quote elements, (d) all three produce chunks with non-null `chunk_id`

### Implementation for User Story 5

- [X] T038 [US5] Extend `SemanticBoundaryEvaluator` in `src/core/chunking/evaluator.py` to correctly compute `code_integrity` (False when either side is `code-block` and the other is not), `quote_integrity` (False when either side is `quote` and the other is not), and `structural_compatibility` for the four new types using the A/B/C/D compatibility groups from research R8
- [X] T039 [US5] Extend `RuleBasedBoundaryDecisionPolicy` in `src/core/chunking/strategies/semantic_structural.py` to fire the priority-1 structural integrity rule (`applied_rule="structural_integrity"`) when `code_integrity=False` or `quote_integrity=False` for the new types; ensure `figure-placeholder` with `structural_compatibility=False` also triggers type incompatibility split at priority 6
- [X] T040 [US5] Extend `ChunkBuilder._heading_stack` tracking in `src/core/chunking/builder.py` to treat `heading` elements as section anchors (push to heading stack on append; pop on a new heading at same or higher level); emit `heading_path` from the current stack into `StructuralContext` for every chunk; propagate to `chunk.metadata["heading_path"]`

**Checkpoint**: `pytest tests/unit/chunking/test_extended_types.py -v` passes; code/quote/figure chunks are always atomic.

---

## Phase 8: User Story 6 — Automated Chunk Quality Validation Gate (Priority: P3)

**Goal**: The validation gate catches 100% of injected quality violations and surfaces them in a structured `ValidationReport` before output reaches indexing.

**Independent Test**: `cd src && pytest tests/unit/chunking/test_validation.py tests/unit/chunking/test_serialization.py tests/unit/chunking/test_builder_lifecycle.py -v`

### Tests for User Story 6 ⚠️

> Write these tests FIRST and confirm they FAIL before implementing T044–T047.

- [X] T041 [P] [US6] Write `tests/unit/chunking/test_validation.py` with injected-violation fixture chunks targeting each of the 6 rules: empty chunk (`min_content`), oversized unsplit chunk (`max_size`), lone heading with no child or following content (`no_orphaned_heading`), chunk whose `lineage.source_element_ids` span two sections (`no_cross_section_merge`), table-row chunk split at character boundary (`no_mid_row_split`), chunk with `parent_chunk_id` referencing a non-existent id (`referential_integrity`); assert each appears in `failed_rules` or `warnings` (SC-007)
- [X] T042 [P] [US6] Write `tests/unit/chunking/test_serialization.py`: round-trip `BoundaryFeatures` and `BoundaryDecision` through `model_dump() → json.dumps() → json.loads() → model_validate()` and assert equality; check all 11 BoundaryFeatures fields survive; check no field is coerced or lost (SC-013)
- [X] T043 [P] [US6] Write `tests/unit/chunking/test_builder_lifecycle.py`: instrument `ChunkBuilder` to record when `chunk_id` and `parent_chunk_id` are first set; assert neither is set before `close_chunk()` completes (FR-047); assert no `BoundaryDecision` or `ValidationReport` instance has a numeric field at the root level (SC-016)

### Implementation for User Story 6

- [X] T044 [US6] Replace the stub `ChunkValidator` in `src/core/chunking/validator.py` with the full implementation: apply all 6 named quality rules in sequence (min_content, max_size, no_orphaned_heading, no_cross_section_merge, no_mid_row_split, referential_integrity) and the `figure_provenance` warning; collect all violations before returning; produce exactly one `ValidationReport` with `status`, `failed_rules`, `warnings`, `validation_messages`; validator MUST NOT mutate or reorder chunks
- [X] T045 [US6] Add re-run consistency test to `test_validation.py`: call `ChunkValidator.validate()` on the same chunk set twice and assert the two `ValidationReport` instances are equal (SC-014)
- [X] T046 [US6] Add `ValidationReport` human-readability check to `test_validation.py`: for every `rule_id` in `failed_rules` + `warnings`, assert a corresponding entry exists in `validation_messages` with a non-empty string (FR-046 structured report contract)

**Checkpoint**: `pytest tests/unit/chunking/test_validation.py tests/unit/chunking/test_serialization.py tests/unit/chunking/test_builder_lifecycle.py -v` all pass; ValidationReport is never a bare boolean.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Observability, benchmarks, backward-compat gate, documentation alignment.

- [X] T047 [P] Add structured logging in `src/tasks/file_processing.py` at the Celery task boundary: log `strategy_id`, per-element-type chunk counts from `ChunkSet.element_counts_by_type`, validation `status`, count of `failed_rules` and `warnings` (NFR-007); use existing `logger` at INFO level with key-value structured format consistent with the rest of the task
- [X] T048 [P] Create `tests/integration/benchmarks/test_chunking_benchmark.py` with a 20-document fixture set (reuse existing fixture DocumentModels from prior test phases); measure median per-document wall-clock time for both the old `map_elements_to_chunks` path (kept as a reference import) and the new engine; record results to `tests/integration/benchmarks/chunking_baseline.json`; assert new engine ≤ 2× old median (SC-008)
- [X] T049 [P] Add docstring to `src/core/chunking/engine.py` explaining the Boundary Decision Pipeline, referencing the plan, and marking the existing shim functions (`row_chunk_dataframe`, `row_chunk_xlsx`) as backward-compat shims that internally call the new strategy (or retain as-is if callers still rely on them directly)
- [X] T050 Run the full quickstart.md validation suite (all 9 Scenarios): execute each `pytest` command from the quickstart, confirm all pass, note any failures as follow-up issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — first story; no inter-story dependency
- **US2 (Phase 4)**: Depends on Phase 2 + Phase 3 (requires a working default strategy to swap from)
- **US3 (Phase 5)**: Depends on Phase 2 + Phase 3 (extends ChunkBuilder from US1)
- **US4 (Phase 6)**: Depends on Phase 2 + Phase 3 + Phase 5 (identity uses relationships for consistency)
- **US5 (Phase 7)**: Depends on Phase 2 + Phase 3 (extends evaluator + policy from US1); can run in parallel with US3/US4
- **US6 (Phase 8)**: Depends on Phase 2 + Phase 3 + Phase 5 (needs relationships for referential integrity rule); can run after US3
- **Polish (Phase 9)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 2 (Foundational)
    ├── US1 (P1) ← MVP start
    │   ├── US2 (P1) — strategy swap
    │   ├── US3 (P1) — relationships (extends ChunkBuilder)
    │   │   └── US6 (P3) — validation (needs referential integrity live)
    │   ├── US4 (P2) — identity/lineage (extends ChunkBuilder, after US3)
    │   └── US5 (P2) — extended types (extends evaluator, parallel with US3/US4)
    └── Polish
```

### Within Each Story

- Test tasks MUST be written first and FAIL before implementation begins
- Models/interfaces before services/strategies
- Strategy implementation before file_processing.py integration
- Each phase checkpoint must pass before moving to the next

### Parallel Opportunities

**Phase 1**: T001, T002, T003 all parallel (different directories/files)

**Phase 2**: T006, T007, T009, T010, T011 all parallel; T008 after T007; T012 after T008

**Phase 3**: T013 and T014 parallel; T015 and T016 parallel (evaluator/policy independent); T017 after T015+T016; T018 after T017; T019 after T018; T020 after T019

**Phase 4**: T021 parallel with T022; T023-T025 after T022

**Phase 5**: T026 parallel with implementation start; T027 → T028 → T029 → T030 sequential (ChunkBuilder extensions)

**Phase 6**: T031 parallel with T032; T032-T035 sequential in ChunkBuilder

**Phase 7**: T036 and T037 parallel; T038 and T039 parallel (evaluator/policy independent); T040 after T038+T039

**Phase 8**: T041, T042, T043 all parallel (test files only); T044 → T045 → T046 sequential (validator implementation then tests)

**Phase 9**: T047, T048, T049 all parallel

---

## Parallel Execution Examples

### Phase 3 (US1) — Parallel Launch

```bash
# Write tests + fixture in parallel (both read-only design docs):
Task: "Create tests/fixtures/chunking/heading_table_sections.py"   # T013
Task: "Write tests/unit/chunking/test_semantic_boundaries.py"      # T014

# Then implement evaluator + policy in parallel:
Task: "Implement SemanticBoundaryEvaluator in evaluator.py"        # T015
Task: "Implement RuleBasedBoundaryDecisionPolicy in strategies/"   # T016
```

### Phase 7 (US5) — Parallel Launch

```bash
# Write tests + fixture in parallel:
Task: "Create tests/fixtures/chunking/extended_types.py"           # T036
Task: "Write tests/unit/chunking/test_extended_types.py"           # T037

# Then extend evaluator + policy in parallel:
Task: "Extend SemanticBoundaryEvaluator for new types"             # T038
Task: "Extend RuleBasedBoundaryDecisionPolicy for new types"       # T039
```

### Phase 8 (US6) — Parallel Launch

```bash
# All three test files in parallel:
Task: "Write test_validation.py"                                   # T041
Task: "Write test_serialization.py"                                # T042
Task: "Write test_builder_lifecycle.py"                            # T043
```

---

## Implementation Strategy

### MVP First (User Stories 1–3 Only)

1. Complete Phase 1: Setup (~15 min)
2. Complete Phase 2: Foundational (blocking — complete before all stories)
3. Complete Phase 3: User Story 1 → `pytest tests/unit/chunking/test_semantic_boundaries.py` passes
4. **STOP and VALIDATE**: existing integration tests still green
5. Complete Phase 4: User Story 2 → strategy swap verified
6. Complete Phase 5: User Story 3 → relationships verified
7. **DEMO**: chunking pipeline running with semantic boundaries, strategy swappability, and relationship-aware output

### Full Delivery (All 6 Stories)

After MVP:
- Phase 6 (US4): identity + lineage → production-grade reproducibility
- Phase 7 (US5): extended types → code/quote/figure as atomic units
- Phase 8 (US6): full validation gate → production safety net
- Phase 9: observability + benchmarks + quickstart sign-off

### Parallel Team Strategy

With multiple developers after Phase 2:
- Developer A: US1 → US2 (evaluator, policy, strategy, integration)
- Developer B: US3 → US4 (ChunkBuilder relationships, identity/lineage)
- Developer C: US5 → US6 (extended types, validation gate)

All three merge back into one branch; no inter-developer coupling until US4 depends on US3's ChunkBuilder.

---

## Notes

- `[P]` tasks operate on different files with no in-progress dependencies — safe to parallelize
- `[Story]` label maps every task to a user story for traceability and independent testing
- Each phase ends with a checkpoint — verify it before starting the next phase
- Tests MUST fail before implementation begins (TDD gate per constitution VII)
- Existing shim functions in `core/chunking/engine.py` (`row_chunk_dataframe`, `row_chunk_xlsx`) are preserved as backward-compat wrappers; they internally call `map_elements_to_chunks` still — update them in Phase 9 (T049) if callers are ready
- `map_elements_to_chunks` in `core/document_intelligence/chunk_mapper.py` is NOT deleted — it remains as the reference implementation and as a benchmark baseline target; the Celery task is the only call site that switches to the new engine
