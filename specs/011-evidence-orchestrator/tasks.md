# Tasks: Evidence Orchestrator

**Input**: Design documents from `specs/011-evidence-orchestrator/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Required per constitution Principle VII. Test tasks are included for every
user story using the `pytest` + `pytest-asyncio` stack established in the plan.

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story. All five user stories from spec.md are covered.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5 map to spec.md)
- Exact file paths are included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the module skeleton and field-pack configuration files.
No logic yet — structure only.

- [X] T001 Create module directory tree: `src/core/evidence_orchestrator/` with sub-packages `collection/`, `deduplication/`, `expansion/`, `compression/`, `prioritization/`, `packaging/`, `token_counting/` — each with an empty `__init__.py`
- [X] T002 [P] Create `src/fields/generic/evidence_orchestrator.yaml` with all keys from `EvidenceOrchestratorConfig` defaults (dedup thresholds, fusion_weights, compressibility_weights, token_counter, celery_offload_threshold, schema_version)
- [X] T003 [P] Create `src/fields/pharmacy/evidence_orchestrator.yaml` with domain overrides: `fusion_weights.entity: 0.4`, `fusion_weights.retrieval: 0.5`, `fusion_weights.recency: 0.1`
- [X] T004 [P] Create `src/fields/legal/evidence_orchestrator.yaml` with domain overrides: `fusion_weights.recency: 0.2`, `fusion_weights.retrieval: 0.5`, `fusion_weights.entity: 0.3`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain types, protocol interfaces, configuration, and token-counting
utilities that every user story depends on. No stage implementations yet.

**⚠️ CRITICAL**: All user story phases depend on this phase being complete first.

- [X] T005 Create `src/core/evidence_orchestrator/errors.py` — `EvidenceOrchestratorError` base class + subclasses: `CollectionError`, `DeduplicationError`, `ExpansionError`, `CompressibilityScoringError`, `PrioritizationError`, `PackagingError`, `EvidencePackVersionError`
- [X] T006 [P] Create `src/core/evidence_orchestrator/models.py` — frozen Pydantic models: `Citation`, `EvidenceItemSource`, `EvidenceItem` (with all fields from data-model.md including `item_id`, `doc_id`, `chunk_id`, `section_path`, `entity_tags`, `relation_tags`, `citation`, `text`, `relevance_score`, `compressibility_score`, `sources`, `expanded`), `CollectedItem`, `OrchestratorStageTrace`, `OrchestratorTrace`, `EvidencePack` (with `is_empty` model validator enforcing `len(items)==0`)
- [X] T007 [P] Create `src/core/evidence_orchestrator/interfaces.py` — abstract base classes: `IEvidenceCollector.collect()`, `IDeduplicator.deduplicate()`, `IEvidenceExpander.expand()`, `ICompressibilityScorer.score()`, `IEvidencePrioritizer.prioritize()`, `IChunkReader.get_chunk()`, `ITokenCounter.count_tokens()`
- [X] T008 Create `src/core/evidence_orchestrator/config.py` — `FusionWeights`, `CompressibilityWeights` (each with sum-to-1.0 validator ± 0.001), `EvidenceOrchestratorConfig` (extra=forbid, all fields from data-model.md config section)
- [X] T009 [P] Create `src/core/evidence_orchestrator/token_counting/character_approximation.py` — `CharacterApproximationTokenCounter(ITokenCounter)`: `count_tokens(text) = ceil(len(text) / 4)`
- [X] T010 [P] Create `src/core/evidence_orchestrator/token_counting/tiktoken_counter.py` — `TiktokenTokenCounter(ITokenCounter)`: wraps `tiktoken.get_encoding()`; raises `ImportError` with clear message if tiktoken not installed
- [X] T011 Create `src/core/evidence_orchestrator/registry.py` — `EvidenceOrchestratorRegistry`: holds references to one concrete impl of each interface; provides `build_orchestrator(config) -> EvidenceOrchestrator` factory method; default wiring uses `RetrievalResultCollector`, `EmbeddingDeduplicator`, `LineageExpander`, `RedundancyScorer`, `FusionPrioritizer`, `PackAssembler`
- [X] T012 [P] Create `tests/unit/core/evidence_orchestrator/__init__.py` and `tests/unit/core/evidence_orchestrator/conftest.py` — shared fixtures: `minimal_retrieval_result()`, `minimal_retrieval_plan()`, `default_config()`, `mock_chunk_reader()`, `mock_embedding_provider()`
- [X] T013 [P] Create `tests/unit/core/evidence_orchestrator/test_models.py` — tests for: `EvidencePack` `is_empty` validator (consistent + inconsistent), `EvidenceItem` field-range validators (`relevance_score` and `compressibility_score` clamped to [0,1]), `Citation` non-empty string validators, `FusionWeights` and `CompressibilityWeights` sum-to-1.0 validators, `pack_id` and `item_id` hash prefix ("ep_", "ei_")

**Checkpoint**: Domain types, interfaces, config, and token counters exist. All model
tests pass. User story implementation can now begin.

---

## Phase 3: User Story 1 — Deduplicated Evidence Pack (Priority: P1) 🎯 MVP

**Goal**: Given a `RetrievalResult` with candidates from two or more retrieval
strategies (including deliberate exact and near duplicates), produce a deduplicated
`CollectedItem` list where each unique chunk appears at most once, with the highest
score retained and both source strategies recorded.

**Independent Test**: `pytest tests/unit/core/evidence_orchestrator/test_collector.py tests/unit/core/evidence_orchestrator/test_deduplicator.py -v`

### Tests for User Story 1 ⚠️

- [X] T014 [P] [US1] Create `tests/unit/core/evidence_orchestrator/test_collector.py` — tests: single candidate → one `CollectedItem`; empty candidates → empty list; `strategy_id` populated from `RetrievalTrace`; `raw_token_count` computed via character approximation; `source_ref=None` candidate handled without error
- [X] T015 [P] [US1] Create `tests/unit/core/evidence_orchestrator/test_deduplicator.py` — tests matching quickstart Scenarios 2–4: exact duplicate merge (highest score kept, sources unioned); zero duplicates passthrough; near-duplicate cosine merge (mock embedding returns identical vectors); character n-gram fallback triggered when `len(items) > dedup_near_batch_limit`; embedding provider unavailable → falls back to char n-gram + structured warning logged; `dedup_near_enabled=False` skips near-dup pass

### Implementation for User Story 1

- [X] T016 [US1] Implement `src/core/evidence_orchestrator/collection/retrieval_result_collector.py` — `RetrievalResultCollector(IEvidenceCollector)`: iterate `result.candidates`, map each `RetrievedCandidate` to `CollectedItem` (strategy_id from matching `RetrievalTrace.steps` by `retriever_id`; raw_token_count via `ITokenCounter`); return list preserving rank order; structured log on entry/exit with `stage="collect"`, `input_count`, `output_count`, `latency_ms`
- [X] T017 [US1] Implement exact-match deduplication pass in `src/core/evidence_orchestrator/deduplication/embedding_deduplicator.py` — `EmbeddingDeduplicator(IDeduplicator)`: group by `chunk_id`; for each group keep the item with the highest `candidate.score`; record all contributing strategy_ids for later source attribution; log `method_used="exact_only"` when near-dup is disabled
- [X] T018 [US1] Extend `EmbeddingDeduplicator` with near-duplicate cosine similarity pass — batch-embed surviving `content_excerpt` strings via `LLMProviderFactory` embedding provider; compute cosine similarity matrix (numpy); merge pairs above `config.dedup_similarity_threshold`; apply same merge rule (highest score wins, sources unioned); log `method_used="embedding"`
- [X] T019 [US1] Extend `EmbeddingDeduplicator` with character n-gram Jaccard fallback — when `len(items) > config.dedup_near_batch_limit` or when embedding provider raises, skip cosine pass and use character n-gram (n=3) Jaccard similarity instead; log `method_used="character_ngram"` + item count + structured warning
- [X] T020 [US1] Verify all `test_deduplicator.py` scenarios pass; confirm `test_collector.py` green; confirm no linter errors in `collection/` and `deduplication/` packages

**Checkpoint**: Collect + Dedup stages independently verified. A deduplicated
`CollectedItem` list is now producible from any `RetrievalResult`.

---

## Phase 4: User Story 2 — Ranked Evidence Pack with Relevance Fusion (Priority: P1)

**Goal**: Given a deduplicated list of `EvidenceItem` objects and a `RetrievalPlan`
with resolved entities, produce a list sorted descending by `relevance_score` that
fuses retrieval score, entity-match ratio, and recency signal using configurable weights.

**Independent Test**: `pytest tests/unit/core/evidence_orchestrator/test_fusion_prioritizer.py -v`

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] Create `tests/unit/core/evidence_orchestrator/test_fusion_prioritizer.py` — tests matching quickstart Scenarios 8 + spec acceptance scenarios: two items with equal retrieval score but different entity matches → entity-rich item ranks higher; items with no plan entities → entity_match_ratio=0.0 for all, ranking by retrieval only; items with recency metadata present → more-recent item boosted; single item → returned with score computed normally; empty input → empty list returned; output is sorted descending

### Implementation for User Story 2

- [X] T022 [US2] Implement `src/core/evidence_orchestrator/prioritization/fusion_prioritizer.py` — `FusionPrioritizer(IEvidencePrioritizer)`: skeleton with `async def prioritize(items, plan, config) -> list[EvidenceItem]`; structured log on entry/exit with `stage="prioritize"`, `input_count`, `latency_ms`
- [X] T023 [US2] Add min-max normalization of `candidate.score` across all items in `fusion_prioritizer.py` — when all scores are equal, set normalized score to 1.0 for all; preserve original score on `EvidenceItem`
- [X] T024 [US2] Add entity-match ratio computation in `fusion_prioritizer.py` — for each item, case-insensitive substring search of each `ResolvedEntity.canonical_form` in `item.text`; `entity_match_ratio = matched_count / max(1, len(plan.entities))`; cap at 1.0; populate `item.entity_tags` with matched canonical forms
- [X] T025 [US2] Add recency scoring and weighted fusion in `fusion_prioritizer.py` — derive `recency_score` from `SourceRef` timestamp if present (min-max normalize across item set; 0.5 neutral when absent); compute `final_score = clamp(w_ret×norm_score + w_ent×entity_ratio + w_rec×recency, 0.0, 1.0)`; assign to `item.relevance_score`; sort items descending; log `entity_matches_total`, `recency_signals_present`

**Checkpoint**: Prioritization stage independently verified. Items can now be ranked
by fused relevance signal.

---

## Phase 5: User Story 5 — Normalized Evidence Pack Output Contract (Priority: P1)

**Goal**: Wire all available stages (collect → dedup → prioritize) into a complete
`EvidenceOrchestrator.orchestrate()` call that returns a schema-valid `EvidencePack`
for any input including empty results. Expansion and compressibility stages run as
pass-throughs at this point (implemented in later phases).

**Independent Test**: `pytest tests/unit/core/evidence_orchestrator/test_pack_assembler.py tests/unit/core/evidence_orchestrator/test_pipeline.py -v`

### Tests for User Story 5 ⚠️

- [X] T026 [P] [US5] Create `tests/unit/core/evidence_orchestrator/test_pack_assembler.py` — tests matching quickstart Scenarios 9–10: `Citation` constructed correctly from `source_ref`; `sources` list non-empty; `token_reduction_ratio` computed and ≤ 0.85 when 90% of inputs are duplicates; `token_reduction_ratio` capped at 1.0 when expansion added tokens; schema_version field equals "1.0.0"
- [X] T027 [P] [US5] Create `tests/unit/core/evidence_orchestrator/test_pipeline.py` — tests matching quickstart Scenarios 1 + 9: smoke (single candidate → valid pack, all mandatory fields non-null); empty candidates → `is_empty=True`, empty items, no exception; `is_empty` validator rejects inconsistent construction; `OrchestratorTrace` has all six stage entries; `pack_id` starts with "ep_"

### Implementation for User Story 5

- [X] T028 [US5] Implement `src/core/evidence_orchestrator/packaging/pack_assembler.py` — `PackAssembler`: construct `Citation` from `RetrievedCandidate.source_ref` + score; build `EvidenceItemSource` per contributing strategy; assemble `EvidenceItem` list; compute `raw_candidate_count`; compute `token_reduction_ratio` using `ITokenCounter` (raw input token count captured before dedup in pipeline); set `is_empty`; populate `strategies_used` from `RetrievalResult.metadata.executed_strategies`; generate `pack_id` ("ep_" + sha256 hash); set `created_at` ISO 8601 UTC; log `stage="package"`
- [X] T029 [US5] Implement `src/core/evidence_orchestrator/pipeline.py` — `EvidenceOrchestrator`: `__init__` accepts registry components; `async def orchestrate(result: RetrievalResult, plan: RetrievalPlan, config: EvidenceOrchestratorConfig) -> EvidencePack`; run stages in order: collect → deduplicate → expand (pass-through if not implemented yet) → compress_flag (pass-through) → prioritize → package; build `OrchestratorStageTrace` per stage (input_count, output_count, latency_ms); assemble `OrchestratorTrace`; propagate stage errors with appropriate `EvidenceOrchestratorError` subclass
- [X] T030 [US5] Add empty-input handling in `pipeline.py` — when `result.candidates` is empty: skip all stages; return `EvidencePack` with `items=[]`, `is_empty=True`, `raw_candidate_count=0`, `token_reduction_ratio=None`; no exception raised
- [X] T031 [US5] Verify all `test_pack_assembler.py` and `test_pipeline.py` scenarios pass; confirm no linter errors across all implemented packages; confirm `EvidenceOrchestrator.orchestrate()` is importable from `src/core/evidence_orchestrator/__init__.py`

**Checkpoint**: Full three-stage pipeline (collect → dedup → prioritize → package)
is end-to-end functional and schema-valid. This is the MVP — all P1 stories done.

---

## Phase 6: User Story 3 — Adjacent Context Expansion (Priority: P2)

**Goal**: High-relevance chunks with prev/next/parent lineage links get their adjacent
context fetched and merged into the `EvidenceItem.text`, with `expanded=True`. Low-score
chunks and disabled config are unaffected.

**Independent Test**: `pytest tests/unit/core/evidence_orchestrator/test_expander.py -v`

### Tests for User Story 3 ⚠️

- [X] T032 [P] [US3] Create `tests/unit/core/evidence_orchestrator/test_expander.py` — tests matching quickstart Scenarios 5–6 + spec acceptance scenarios: high-score chunk with prev link → text prepended, `expanded=True`; high-score chunk with next link → text appended; chunk whose text < `expansion_min_chars` → parent fetched first; score below threshold → unchanged, no fetch; `expansion_enabled=False` → no fetch for any item; `IChunkReader.get_chunk` returns `None` → original text kept, `expanded=False`, warning logged; fetch exception → original text kept, error logged, pipeline continues

### Implementation for User Story 3

- [X] T033 [US3] Implement `src/core/evidence_orchestrator/expansion/lineage_expander.py` — `LineageExpander(IEvidenceExpander)`: `async def expand(items, chunk_reader, config)`; iterate items; skip if `config.expansion_enabled=False` (return immediately); skip if `item.candidate.score < config.expansion_score_threshold`; log `stage="expand"` with `input_count`, `expanded_count`, `fetch_failures`, `expansion_enabled`, `latency_ms`
- [X] T034 [US3] Add parent-chunk expansion logic to `LineageExpander` — when `len(item.text) < config.expansion_min_chars` and `chunk.relationships.parent_chunk_id` is set: fetch parent via `chunk_reader.get_chunk()`; if successful, prepend parent text; set `expanded=True`
- [X] T035 [US3] Add prev/next-chunk expansion logic to `LineageExpander` — fetch `previous_chunk_id` (prepend) and/or `next_chunk_id` (append) when score meets threshold; guard each fetch independently so a failed prev-fetch does not block next-fetch; wrap each fetch in try/except: on `None` result log warning; on exception log error; in both cases keep original text
- [X] T036 [US3] Wire `IChunkReader` concrete implementation in `registry.py` — add `chunk_reader: IChunkReader` parameter to `EvidenceOrchestratorRegistry`; document that the infrastructure layer (outside `src/core/`) is responsible for injecting a `ChunkRepository`-backed instance; provide a `NoOpChunkReader` stub that always returns `None` for use when expansion is disabled or in tests

**Checkpoint**: Expansion stage independently verified. Pipeline now runs all six
stages; expansion activates only for qualifying high-score chunks.

---

## Phase 7: User Story 4 — Compressibility Flagging (Priority: P2)

**Goal**: Every surviving `EvidenceItem` receives an advisory `compressibility_score`
(0.0–1.0) based on redundancy vs. higher-ranked items and its own relevance. High-value
unique items score low; redundant or low-relevance items score high.

**Independent Test**: `pytest tests/unit/core/evidence_orchestrator/test_redundancy_scorer.py -v`

### Tests for User Story 4 ⚠️

- [X] T037 [P] [US4] Create `tests/unit/core/evidence_orchestrator/test_redundancy_scorer.py` — tests matching quickstart Scenario 7 + spec acceptance scenarios: unique high-relevance item → `compressibility_score < 0.3`; near-duplicate survivor (text 90% overlap with higher-ranked item) → `compressibility_score > 0.7`; low-relevance unique item → score reflects relevance-inverse component; single item → redundancy=0.0, score = 0.4 × (1 − relevance_score); empty input → empty list returned; one item fails (empty text) → fallback `compressibility_score=0.5` for that item, rest unaffected; `compressibility_weights` override respected

### Implementation for User Story 4

- [X] T038 [US4] Implement `src/core/evidence_orchestrator/compression/redundancy_scorer.py` — `RedundancyScorer(ICompressibilityScorer)`: `async def score(items, config) -> list[EvidenceItem]`; iterate items in relevance_score descending order (highest-ranked first); maintain a running union set of character 3-grams from all previously processed items' texts; log `stage="compress_flag"`, `input_count`, `output_count`, `high_compressibility_count`, `latency_ms`
- [X] T039 [US4] Add character n-gram Jaccard redundancy computation in `RedundancyScorer` — for item i: `ngrams_i = set of character 3-grams from item.text`; `union_above = union of 3-gram sets of all higher-ranked items`; `redundancy = len(ngrams_i & union_above) / max(1, len(ngrams_i | union_above))`; for the first item (no items above it), `redundancy=0.0`; after computing, add `ngrams_i` to `union_above`
- [X] T040 [US4] Add weighted fusion and assignment in `RedundancyScorer` — `relevance_inverse = 1.0 - item.relevance_score`; `score = clamp(config.compressibility_weights.redundancy × redundancy + config.compressibility_weights.relevance_inverse × relevance_inverse, 0.0, 1.0)`; assign to `item.compressibility_score`; update running union
- [X] T041 [US4] Add per-item error handling in `RedundancyScorer` — wrap each item's computation in try/except; on any exception (e.g. empty `item.text`): assign `compressibility_score=0.5`; log structured error with `item_id`; continue to next item; do not raise

**Checkpoint**: Compressibility stage independently verified. All six pipeline stages
are now fully implemented and tested in isolation.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end integration, latency baseline measurement, public API surface,
and validation against quickstart scenarios.

- [X] T042 [P] Write `tests/integration/test_evidence_orchestrator_e2e.py` — full pipeline integration test matching quickstart Scenario 11: 20-candidate `RetrievalResult` (8 exact duplicates across two strategies, 4 near-duplicates at cosine 0.97, 8 unique); `RetrievalPlan` with 3 resolved entities; mock embedding provider (deterministic vectors); mock `IChunkReader` (canned adjacent chunks for 2 high-score items); assert `len(pack.items) ≤ 12`; `token_reduction_ratio ≤ 0.85` (SC-002); all `EvidenceItem` fields non-null (SC-003); items sorted descending; entity-matched items rank above equal-score items without matches (SC-005); `schema_version == "1.0.0"`
- [X] T043 Add `test_pipeline_latency_benchmark` to `tests/integration/test_evidence_orchestrator_e2e.py` — `@pytest.mark.benchmark` test: 100-candidate synthetic input (50% exact duplicates), mock providers, 20 runs; report p50 and p95 latency; test does NOT fail on latency threshold — records measurement only (SC-004 baseline)
- [X] T044 [P] Finalize `src/core/evidence_orchestrator/__init__.py` — export public API: `EvidenceOrchestrator`, `EvidencePack`, `EvidenceItem`, `Citation`, `EvidenceOrchestratorConfig`, `EvidenceOrchestratorRegistry`, `IEvidenceCollector`, `IDeduplicator`, `IEvidenceExpander`, `ICompressibilityScorer`, `IEvidencePrioritizer`, `IChunkReader`, `ITokenCounter`
- [X] T045 [P] Add `evidence_orchestrator` entry to `src/fields/generic/retrieval.yaml` (or equivalent field registry) so the new YAML file is discovered by the `FieldRegistry` from spec 002
- [X] T046 Run all quickstart.md Scenarios 1–12 and confirm all pass; record `test_pipeline_latency_benchmark` p50 result
- [X] T047 Update `specs/011-evidence-orchestrator/plan.md` SC-004 row with the measured p50 benchmark baseline from T043/T046

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user story phases**
- **Phase 3 (US1)**: Depends on Phase 2 only — no dependency on US2/US5
- **Phase 4 (US2)**: Depends on Phase 2 only — no dependency on US1/US5
- **Phase 5 (US5)**: Depends on Phase 2; benefits from Phase 3 + Phase 4 being done (uses collector + prioritizer), but pipeline.py can stub missing stages as pass-throughs
- **Phase 6 (US3)**: Depends on Phase 2 + Phase 5 (pipeline.py must exist for stage wiring)
- **Phase 7 (US4)**: Depends on Phase 2 + Phase 5 (same reason)
- **Phase 8 (Polish)**: Depends on Phases 3–7 all complete

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2 — no dependency on US2, US3, US4, US5
- **US2 (P1)**: Independent after Phase 2 — no dependency on US1, US3, US4, US5
- **US5 (P1)**: Uses outputs of US1 and US2 stages; can be developed with stubs before they complete
- **US3 (P2)**: Plugs into pipeline after US5 is done
- **US4 (P2)**: Plugs into pipeline after US5 is done; independent of US3

### Within Each Phase

- Write tests before implementation (tests must fail first)
- Models/interfaces before concrete implementations
- Individual stages before pipeline wiring
- Pipeline wiring (T029) before full integration test

---

## Parallel Opportunities

### Phase 1

```
T001 → T002, T003, T004 in parallel
```

### Phase 2

```
T005 first (errors.py, no deps)
T006, T007, T009, T010, T012 in parallel (independent files)
T008 after T006 (config references model types)
T011 after T006, T007 (registry references all interfaces)
T013 after T006 (tests models)
```

### Phase 3 (US1)

```
T014, T015 in parallel (write tests first)
T016 after T015 passes → T017 → T018 → T019 → T020
```

### Phase 4 (US2)

```
T021 (write tests first)
T022 → T023 → T024 → T025 in sequence
T021 can run in parallel with Phase 3 work
```

### Phases 6 and 7 (US3 + US4) — after Phase 5

```
T032 and T037 in parallel (tests for US3 and US4)
T033–T036 (US3) and T038–T041 (US4) in parallel across developers
```

---

## Parallel Example: User Story 1

```
# Step 1 — write tests in parallel:
Task T014: "Create test_collector.py in tests/unit/core/evidence_orchestrator/"
Task T015: "Create test_deduplicator.py in tests/unit/core/evidence_orchestrator/"

# Step 2 — implement collector:
Task T016: "Implement retrieval_result_collector.py in src/core/evidence_orchestrator/collection/"

# Step 3 — implement deduplicator stages sequentially:
Task T017: "Exact-match pass in embedding_deduplicator.py"
Task T018: "Near-dup cosine pass in embedding_deduplicator.py"
Task T019: "Character n-gram fallback in embedding_deduplicator.py"

# Step 4 — verify:
Task T020: "Confirm all test_deduplicator.py and test_collector.py scenarios pass"
```

---

## Implementation Strategy

### MVP First (P1 Stories Only — Phases 1–5)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T013)
3. Complete Phase 3: US1 — Dedup (T014–T020)
4. Complete Phase 4: US2 — Fusion ranking (T021–T025)
5. Complete Phase 5: US5 — Full pack contract + pipeline (T026–T031)
6. **STOP and VALIDATE**: Run quickstart Scenarios 1–10; confirm SC-001 through SC-005

### Incremental Delivery

1. Setup + Foundational → Framework ready
2. US1 → Deduplication works end-to-end → Validate independently
3. US2 → Ranking works → Validate independently
4. US5 → Full EvidencePack produced → MVP deliverable to spec 012
5. US3 → Expansion adds context → Validate independently
6. US4 → Compressibility flagging → Full feature complete
7. Polish → Integration test + benchmark

### Parallel Team Strategy

With multiple developers after Phase 2 completes:
- Developer A: US1 (Phase 3) — collect + dedup
- Developer B: US2 (Phase 4) — fusion prioritization
- Both converge on US5 (Phase 5) — pipeline wiring
- Developer A: US3 (Phase 6) — expansion
- Developer B: US4 (Phase 7) — compressibility
- Both: Phase 8 polish + integration

---

## Task Count Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Phase 1: Setup | T001–T004 | — |
| Phase 2: Foundational | T005–T013 | — |
| Phase 3 | T014–T020 | US1 (P1) |
| Phase 4 | T021–T025 | US2 (P1) |
| Phase 5 | T026–T031 | US5 (P1) |
| Phase 6 | T032–T036 | US3 (P2) |
| Phase 7 | T037–T041 | US4 (P2) |
| Phase 8: Polish | T042–T047 | — |
| **Total** | **47** | |

---

## Notes

- `[P]` tasks have no shared file dependencies within their phase and can be assigned
  to different developers or parallel agent runs
- `[Story]` label maps each task to the spec.md user story for traceability
- Each user story phase is independently completable and testable
- Confirm tests fail before implementing — avoids false confidence
- Commit after each logical group (T014+T015 together, then T016, etc.)
- Stop at Phase 5 checkpoint to validate MVP with spec 012 team before proceeding to P2 stories
