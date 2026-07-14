# Tasks: Answer Quality (Completeness & Accuracy)

**Input**: `specs/005-answer-quality/research.md`  
**Constraint**: Changes live in **core / services / generic templates**. Domain differences only via YAML (`fields/*/retrieval.yaml`, prompts). No new `utils/pharmacy/` (or similar) code.

**Tests**: Required for changed behavior. Golden answer-quality harness is the primary regression gate (AQ-1…AQ-6).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 0: Blocker

- [x] T000 Fix infinite recursion in `src/services/rag/answer_service.py` `_build_retrieval_context` (call `resolve_from_plan` + manifest; do not self-call)

---

## Phase 1: Measurement (must precede “quality” claims)

**Purpose**: Turn “incomplete like NotebookLM isn’t” into numbers.

- [ ] T001 [P] Define golden case schema in `tests/golden/answer_quality/schema.md` (`question`, `context`, `gold_items`, `gold_source_keys`, `expect_refusal`)
- [ ] T002 [P] Add scorer module `src/core/answer_quality/metrics.py` (coverage, list completeness, truncation flag helpers — pure functions)
- [ ] T003 Create runner `scripts/run_answer_quality_golden.py` (load YAML fixtures, call answer path or recorded retrieval+answer dumps, exit non-zero under thresholds)
- [ ] T004 Seed ≥20 list + ≥15 factual + ≥10 refusal fixtures under `tests/golden/answer_quality/` (pharmacy fixtures OK; schema generic)
- [ ] T005 Record first baseline run in `specs/005-answer-quality/baseline.md` (AQ-1…AQ-6 actuals)

**Checkpoint**: Baseline numbers exist. No pipeline behavior change required yet except T000.

---

## Phase 2: Retrieval completeness (G1, G3, G7) — AQ-1

**Goal**: Gold source rows reach the prompt for `scope=all` / list-shaped fields.

- [ ] T006 Add `is_exhaustive_plan(query_plan, field_resolution)` helper in `src/core/retrieval/exhaustiveness.py`
- [ ] T007 [P] Unit tests for exhaustiveness helper in `tests/unit/core/retrieval/test_exhaustiveness.py`
- [ ] T008 Coverage gate in `src/services/rag/answer_service.py`: when exhaustive and `candidate_rows > len(docs)`, top-up via `ChunkModel.list_chunks_for_entity_prefix` (or equivalent) up to configured max
- [ ] T009 Exhaustive rerank policy in `src/services/rag/answer_service.py`: order-only; do not drop below `min(len(docs), retrieval_limit)` / never return empty if pre-rerank non-empty for exhaustive
- [ ] T010 Plan-driven disable of chunk focus in `answer_service._document_text_for_prompt` when exhaustive or `output_shape=list`
- [ ] T011 [P] Add `exhaustive_max_rows` + `coverage_topup_enabled` to `RetrievalProfile` in `src/fields/schemas.py` and `src/fields/generic/retrieval.yaml` (pharmacy overrides limits in its YAML only)

**Checkpoint**: AQ-1 improves on list fixtures vs baseline.

---

## Phase 3: Context packing & generation completeness (G2, G4) — AQ-2, AQ-5

- [ ] T012 Exhaustive packing in `src/services/rag/answer_service.py`: when char budget would truncate >20% of docs, log `context_truncated`, prefer field-value-only packing for list concepts, else raise budget from `profile.config.generation`
- [ ] T013 Completeness footer for exhaustive answers in `src/stores/llm/templates/locales/en/rag.py` (+ `ar` if present): must list every item; if stopping early, state counts
- [ ] T014 Under-count retry once in `src/services/rag/answer_service.py` when retrieved row count ≫ extracted list item count (heuristic in `src/core/answer_quality/list_count.py`)
- [ ] T015 [P] Unit tests for list-count heuristic in `tests/unit/core/answer_quality/test_list_count.py`

**Checkpoint**: AQ-2 and AQ-5 move toward targets on golden set.

---

## Phase 4: Faithfulness (G8) — AQ-3, AQ-4

- [ ] T016 Optional post-answer faithfulness check stub in `src/core/answer_quality/faithfulness.py` (entity/number tokens in answer must appear in context; feature-flagged)
- [ ] T017 Wire flag `RAG_ANSWER_FAITHFULNESS_CHECK` in `src/helpers/config.py` + `.env.example`; on fail, one regenerate or refuse
- [ ] T018 [P] Unit tests in `tests/unit/core/answer_quality/test_faithfulness.py`
- [ ] T019 Ensure refusal fixtures (not in sources) stay at AQ-4 = 100% in golden runner

**Checkpoint**: AQ-3 ≤5% on golden; AQ-4 holds.

---

## Phase 5: YAML retrieval strategies (G6) — keep core generic

- [ ] T020 Extend `RetrievalProfile` / `fields.yaml` concepts with optional `retrieval_strategy: vector_default | entity_prefix_all | structured_pair`
- [ ] T021 Dispatch strategies in `src/services/rag/answer_service.py` (replace hard-coded `field == "interactions"`)
- [ ] T022 Map pharmacy `interactions` → `structured_pair` in `src/fields/pharmacy/fields.yaml` or `retrieval.yaml` only
- [ ] T023 [P] Generic pack keeps `vector_default`; legal unchanged

**Checkpoint**: No domain field name branching in answer_service for retrieval path selection.

---

## Phase 6: Observability & polish

- [ ] T024 Metrics in `src/utils/metrics.py`: `RAG_RETRIEVAL_COVERAGE`, `RAG_CONTEXT_TRUNCATED_TOTAL`, `RAG_LIST_UNDERCOUNT_RETRY_TOTAL`
- [ ] T025 Structured log fields: `candidate_rows`, `docs_in_prompt`, `exhaustive`, `truncated`, `coverage_ratio`
- [ ] T026 Re-run golden runner; update `specs/005-answer-quality/baseline.md` with post-fix scores
- [ ] T027 Update `AGENTS.md` Speckit pointer; mark Phase 2–4 done criteria in `specs/005-answer-quality/plan.md`

---

## Dependencies

```
T000 (done)
 → Phase 1 (T001–T005) measurement
 → Phase 2 (T006–T011) retrieval coverage   ─┐
 → Phase 3 (T012–T015) generation complete ─┼→ Phase 6
 → Phase 4 (T016–T019) faithfulness        ─┘
 Phase 5 (T020–T023) can parallel Phase 3/4 after T008
```

## MVP slice

**T000 + Phase 1 + T006–T010 + T013–T014**: measurable baseline + fix the two biggest incompleteness causes (coverage gate + generation under-count).

## Notes

- Do **not** add pharmacy regex intent trees back.
- Pack YAML may raise `exhaustive_min_limit` / `exhaustive_max_rows`; core must not hardcode 500 for a field name once T021 lands.
- Parser work remains in 004; this feature consumes `QueryPlan` only.
