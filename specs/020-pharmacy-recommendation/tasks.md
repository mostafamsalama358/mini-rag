# Tasks: Pharmacy Recommendation Capability

**Input**: Design documents from `/specs/020-pharmacy-recommendation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, governance/adr-020-001-recommendation-as-capability.md

**Tests**: Required per constitution (Principle VII). Include unit, integration, and architecture tests. No Recommendation Service, Recommendation API, parallel pipeline, or new sole owner ([ADR-020-001](./governance/adr-020-001-recommendation-as-capability.md)).

**Organization**: Tasks grouped by user story for independent delivery. Extensions live under existing Query Understanding, Retrieval, Answer, and pharmacy Domain Pack trees only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US6)
- Every task includes an exact file path

## Path Conventions

- Domain Pack: `src/fields/pharmacy/`
- Query understanding: `src/core/query_parser/`
- Retrieval adapters / orchestrator: `src/services/rag/`
- Answer composition: `src/core/answer_generation/`
- Architecture tests: `tests/architecture/`
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Feature artifacts: `specs/020-pharmacy-recommendation/`
- Eval bridge (019 hosts runners): `specs/019-rag-evaluation-framework/governance/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold pack + module layout and architecture guards shared by all stories.

- [X] T001 Create recommend capability README describing capability-only scope (no service/API/pipeline) in `specs/020-pharmacy-recommendation/governance/README.md`
- [X] T002 [P] Add pharmacy recommend pack directory note and file list in `src/fields/pharmacy/README_recommend.md` (taxonomy, policy, safety subset, indication tags)
- [X] T003 [P] Create empty symptom taxonomy stub YAML in `src/fields/pharmacy/symptom_taxonomy.yaml` with version + nodes[] + indication_tags[] schema comments aligned to `data-model.md`
- [X] T004 [P] Create empty recommendation policy stub YAML in `src/fields/pharmacy/recommendation_policy.yaml` with signal weight placeholders, max_recommendations, clarification_confidence_threshold keys (values pack-owned; document “no hardcoded architecture weights”)
- [X] T005 [P] Create empty safety model subset stub YAML in `src/fields/pharmacy/safety_model.yaml` enabling pregnancy + breastfeeding for v1 and listing future dimensions as inactive
- [X] T006 [P] Ensure `tests/architecture/README.md` documents 020 suite markers (ADR-020-001, frozen `/answer`, no parallel recommend path)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models, pack loaders, sole-path guards, and orchestrator hooks that ALL user stories need. **Blocks all user stories.**

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T007 Add `NeedFrame` Pydantic model (optional fields per `data-model.md`) in `src/core/query_parser/need_frame.py`
- [X] T008 [P] Add `ProductIdentity`, `SafetyLabel`, `RankingSignals`, `RecommendationCandidate`, `RecommendationDecision` models in `src/services/rag/recommend/models.py` (package is internal helper under rag — NOT a production Recommendation Service owner)
- [X] T009 [P] Add `RecommendationTrace` model in `src/services/rag/recommend/trace.py`
- [X] T010 Extend `QueryPlan` / parse schema to carry recommend intent + optional `need_frame` without breaking existing plans in `src/core/query_parser/schema.py` (keep `extra` policy compatible; prefer additive optional fields + operation/intent extension documented in module docstring)
- [X] T011 [P] Add Domain Pack loaders for `symptom_taxonomy.yaml`, `recommendation_policy.yaml`, `safety_model.yaml` in `src/fields/pharmacy/recommend_pack.py`
- [X] T012 [P] Wire pharmacy pack file discovery so new YAMLs merge/load with existing pack resolution in `src/fields/` loader module used by pharmacy domain (update the existing pack registry/entry point file that already loads `parser.yaml` / `answer_generation.yaml`)
- [X] T013 Add failing architecture test forbidding Recommendation Service/API route modules in `tests/architecture/test_020_no_recommendation_service_or_api.py` (assert no `routes/**/recommend*.py` production endpoint and ADR-020-001 file exists)
- [X] T014 [P] Add architecture test that frozen `/answer` request/response field names remain unchanged in `tests/architecture/test_020_answer_contract_frozen.py` (compare against `specs/015-unified-pipeline-migration/contracts/api-stability.md` field lists)
- [X] T015 [P] Add unit test stubs (xfail/fail-first) for NeedFrame validation in `tests/unit/core/query_parser/test_need_frame.py`
- [X] T016 Document foundational ownership map (Query Understanding / Retrieval / Answer / Pack / 019) in `specs/020-pharmacy-recommendation/governance/ownership-map.md` citing `contracts/ownership-and-flow.md`

**Checkpoint**: Models + pack stubs + sole-path architecture guards exist — user stories can proceed.

---

## Phase 3: User Story 1 — Ask for a medicine by need (Priority: P1) 🎯 MVP

**Goal**: Need-based queries without a brand return a short ranked list of in-corpus products with grounded reasons and citations (corpus-bounded).

**Independent Test**: With indication-tagged products for acidity, ask “دواء للحموضة؟”; assert recommend-mode answer cites ≥1 in-corpus candidate and invents no out-of-catalog brands. Unit tests for taxonomy mapping + ranking composition pass.

### Tests for User Story 1

- [X] T017 [P] [US1] Unit test Symptom Taxonomy many-to-many + AR/EN normalization in `tests/unit/fields/pharmacy/test_symptom_taxonomy.py`
- [X] T018 [P] [US1] Unit test Recommendation Score signal composition (no fixed weights; policy-driven) in `tests/unit/services/rag/recommend/test_ranking.py`
- [X] T019 [P] [US1] Unit test corpus-boundedness helper rejects out-of-corpus product ids in `tests/unit/services/rag/recommend/test_corpus_bounded.py`
- [X] T020 [P] [US1] Integration smoke: recommend intent on `/answer` keeps frozen response keys in `tests/integration/test_020_recommend_answer_contract.py`

### Implementation for User Story 1

- [X] T021 [P] [US1] Populate priority Symptom Taxonomy nodes (acidity, migraine/headache, diarrhea, pain/fever at minimum) with AR/EN synonyms in `src/fields/pharmacy/symptom_taxonomy.yaml`
- [X] T022 [P] [US1] Author indication tag vocabulary + product→tag mapping seed for priority buckets in `src/fields/pharmacy/indication_tags.yaml`
- [X] T023 [US1] Implement taxonomy mapper (phrase → nodes/tags + confidence) in `src/fields/pharmacy/taxonomy_mapper.py`
- [X] T024 [US1] Detect recommend/need-based intent and populate `NeedFrame` in `src/core/query_parser/parser.py` + pharmacy `src/fields/pharmacy/parser.yaml` prompt/rules
- [X] T025 [US1] Apply candidate constraints + metadata filtering for indication tags on sole retrieval path in `src/services/rag/adapters/scope.py` and/or `src/services/rag/recommend/constraints.py`
- [X] T026 [US1] Implement Recommendation Ranking composition (Indication Match, Retrieval Evidence, Reranker Confidence, Safety Fitness stub-pass, optional formulary) in `src/services/rag/recommend/ranking.py` reading weights from `recommendation_policy.yaml`
- [X] T027 [US1] Integrate recommend branch into sole orchestrator flow (logical steps; no new pipeline owner) in `src/services/rag/pipeline/unified_orchestrator.py`
- [X] T028 [US1] Add recommend-mode answer capability module (ranked options + citations + consult caveat) in `src/fields/pharmacy/answer_generation.yaml` and ensure composer picks it up via `src/core/answer_generation/composition/default_composer.py`
- [X] T029 [US1] Enforce max recommendations + never-out-of-corpus hard rules from policy in `src/services/rag/recommend/policy.py`
- [X] T030 [US1] Add structured logging for recommend-mode (correlation id, decision_type, candidate_count) in `src/services/rag/diagnostics.py`

**Checkpoint**: MVP — need-based acidity/migraine-style questions return corpus-bounded ranked recommendations on `/answer`.

---

## Phase 4: User Story 2 — Safety-aware recommendations (Priority: P1)

**Goal**: Population/context constraints apply Safety Filtering; avoid/contraindicated options are excluded or demoted; unknown ≠ safe.

**Independent Test**: Pain/fever need + pregnancy → pregnancy avoid/contraindicated products are not silent first-line; unit tests for safety filter pass on v1 subset.

### Tests for User Story 2

- [X] T031 [P] [US2] Unit test Safety Filtering for pregnancy/breastfeeding dimensions in `tests/unit/services/rag/recommend/test_safety_filter.py`
- [X] T032 [P] [US2] Unit test unknown safety label does not equal safe in `tests/unit/services/rag/recommend/test_safety_unknown.py`
- [X] T033 [P] [US2] Integration test pregnancy-constrained recommend posture in `tests/integration/test_020_recommend_safety_pregnancy.py`

### Implementation for User Story 2

- [X] T034 [P] [US2] Complete v1 `safety_model.yaml` enums/actions (pass/demote/exclude/unknown) in `src/fields/pharmacy/safety_model.yaml`
- [X] T035 [US2] Implement Safety Filtering + Safety Fitness signal in `src/services/rag/recommend/safety.py`
- [X] T036 [US2] Map NeedFrame.population (and related) into safety constraints before final ranking in `src/services/rag/recommend/constraints.py`
- [X] T037 [US2] When only high-risk candidates remain, emit refuse/consult decision via `RecommendationDecision` in `src/services/rag/recommend/decision.py`
- [X] T038 [US2] Surface safety caveats in recommend answer module copy in `src/fields/pharmacy/answer_generation.yaml`
- [X] T039 [US2] Ensure ingestible safety metadata keys documented for leaflet/chunk metadata in `src/fields/pharmacy/chunk_metadata.yaml` (and/or fields.yaml) without a second ingest path

**Checkpoint**: Safety-aware recommend works for pregnancy/breastfeeding subset; extensible catalog remains for future dimensions.

---

## Phase 5: User Story 3 — Ambiguous need clarification (Priority: P2)

**Goal**: Broad/multi-bucket needs trigger bounded clarification (existing `needs_clarification` signals) instead of an unfocused dump.

**Independent Test**: Underspecified need (“مشكلة في البطن” / “cold”) → clarification or narrowly scoped groups; taxonomy ambiguity detection unit tests pass.

### Tests for User Story 3

- [X] T040 [P] [US3] Unit test ambiguity_group / multi-bucket detection in `tests/unit/fields/pharmacy/test_taxonomy_ambiguity.py`
- [X] T041 [P] [US3] Unit test clarification threshold from recommendation policy in `tests/unit/services/rag/recommend/test_clarification_policy.py`
- [X] T042 [P] [US3] Integration test ambiguous need returns `needs_clarification=true` with frozen keys in `tests/integration/test_020_recommend_clarification.py`

### Implementation for User Story 3

- [X] T043 [P] [US3] Add ambiguity groups + clarification prompts to taxonomy nodes in `src/fields/pharmacy/symptom_taxonomy.yaml`
- [X] T044 [US3] Implement clarify-instead-of-guessing decision path in `src/services/rag/recommend/decision.py`
- [X] T045 [US3] Populate `QueryPlan.needs_clarification` + `clarification_prompt` for low-confidence / multi-bucket recommend intents in `src/core/query_parser/parser.py`
- [X] T046 [US3] Ensure orchestrator short-circuits to clarification response without fabricating candidates in `src/services/rag/pipeline/unified_orchestrator.py`

**Checkpoint**: Ambiguous needs clarify via existing answer contract signals.

---

## Phase 6: User Story 4 — Compare among need-matched options (Priority: P2)

**Goal**: Compare need-matched products using retrieved evidence only; no hidden-score storytelling or unsupported clinical superiority.

**Independent Test**: From an acidity candidate set, compare two products with field-grounded citations; Explanation Policy unit checks pass.

### Tests for User Story 4

- [X] T047 [P] [US4] Unit test Explanation Policy guards (no hidden-score language patterns / superiority without evidence flag) in `tests/unit/core/answer_generation/test_recommend_explanation_policy.py`
- [X] T048 [P] [US4] Integration test compare-after-recommend keeps citations and frozen contract in `tests/integration/test_020_recommend_compare.py`

### Implementation for User Story 4

- [X] T049 [P] [US4] Add recommend-compare capability instructions (evidence-only; no clinical superiority without evidence; recommendation ≠ medical advice) in `src/fields/pharmacy/answer_generation.yaml`
- [X] T050 [US4] Implement Explanation Policy helper applied during recommend/compare compose in `src/core/answer_generation/composition/recommend_explanation_policy.py`
- [X] T051 [US4] Ensure compare operation with prior recommend candidates reuses multi-entity compare path without new API in `src/services/rag/pipeline/unified_orchestrator.py` and/or existing compare planning in `src/core/retrieval_planner/`
- [X] T052 [US4] Document Product Identity disambiguation for compare pairs in `src/services/rag/recommend/identity.py` and call from ranking/decision

**Checkpoint**: Compare among recommend candidates is evidence-grounded and policy-safe.

---

## Phase 7: User Story 5 — Evaluation and regression gates (Priority: P2)

**Goal**: Recommend-mode is evaluable under Feature 019 via golden set + profile bridge (020 defines catalog; 019 owns runners). Architecture tests enforce metric catalog presence and corpus-boundedness/safety gate intent.

**Independent Test**: Golden set + 019 profile index entry exist; architecture tests for metric catalog and defect-attribution buckets pass; a forbidden out-of-corpus case is marked as must-fail under Corpus-Boundedness / False Recommendation Rate.

### Tests for User Story 5

- [X] T053 [P] [US5] Architecture test recommend metric catalog completeness in `tests/architecture/test_020_recommend_metric_catalog.py` (Recall@K, Precision@K, MRR, nDCG, Safety Precision/Recall, False Recommendation Rate, Clarification Rate, Corpus-Boundedness, Recommendation Diversity)
- [X] T054 [P] [US5] Architecture test 019 profile bridge entry exists for pharmacy recommend in `tests/architecture/test_020_019_recommend_profile_bridge.py`
- [X] T055 [P] [US5] Unit/golden schema test for RecommendEvalCase fixtures in `tests/unit/eval/test_020_recommend_eval_case_schema.py`

### Implementation for User Story 5

- [X] T056 [P] [US5] Publish recommend metric catalog + attribution buckets in `specs/020-pharmacy-recommendation/governance/recommend-metric-catalog.md` (mirror `contracts/evaluation-bridge.md`)
- [X] T057 [P] [US5] Add pharmacy recommendation profile row/section to `specs/019-rag-evaluation-framework/governance/evaluation-profile-index.md` (dataset tier classes, enabled metrics, gate type — no request-path eval; no claiming 020 owns runners)
- [X] T058 [US5] Author initial RecommendEvalCase golden set (≥20 queries / ≥5 buckets where feasible; include pregnancy safety + ambiguous clarification cases) in `specs/020-pharmacy-recommendation/eval/recommend_golden_v1.jsonl`
- [X] T059 [P] [US5] Document how to run/bridge offline scoring under 019 (placeholder runner ownership) in `specs/020-pharmacy-recommendation/governance/eval-runbook.md`
- [X] T060 [US5] Add defect-attribution mapping (taxonomy vs retrieval vs ranking vs safety vs generation) in `specs/020-pharmacy-recommendation/governance/defect-attribution.md`

**Checkpoint**: Recommend eval is defined and bridged to 019; ready for runner implementation under 019 tasks/ownership.

---

## Phase 8: User Story 6 — Operator visibility into recommend decisions (Priority: P3)

**Goal**: Operators can inspect Need Frame, matched indications, evidence pointers, safety outcomes, and rank contributions via Recommendation Trace / diagnostics — without breaking public API or dumping hidden scores to end users.

**Independent Test**: For a safety-filtered case, diagnostics/trace shows exclusion reason + rank contributions for retained candidates; end-user answer remains evidence-only.

### Tests for User Story 6

- [X] T061 [P] [US6] Unit test RecommendationTrace required fields (matched indications, safety outcome, rank contribution) in `tests/unit/services/rag/recommend/test_trace.py`
- [X] T062 [P] [US6] Unit test end-user answer redaction does not require raw weight tables in `tests/unit/core/answer_generation/test_recommend_no_hidden_scores.py`
- [X] T063 [P] [US6] Integration/diagnostic test trace attached for recommend-mode in `tests/integration/test_020_recommend_trace_diagnostics.py`

### Implementation for User Story 6

- [X] T064 [US6] Populate RecommendationTrace during recommend decisions in `src/services/rag/recommend/trace.py` + call sites in `src/services/rag/recommend/decision.py`
- [X] T065 [US6] Emit recommend trace via existing diagnostics/quality context surfaces in `src/services/rag/diagnostics.py` (and Quality Context hook if present under 018-aligned modules)
- [X] T066 [US6] Ensure Product Identity Rules affect trace identity_level fields in `src/services/rag/recommend/identity.py`
- [X] T067 [US6] Document operator how-to for reading recommend traces in `specs/020-pharmacy-recommendation/governance/operator-trace-guide.md`

**Checkpoint**: Operator explainability complete without public API break.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story hardening, ingest notes, quickstart validation, docs.

- [X] T068 [P] Implement Product Identity collapse/slotting rules fully (brand→line→strength→package) in `src/services/rag/recommend/identity.py` with unit tests in `tests/unit/services/rag/recommend/test_product_identity.py`
- [X] T069 [P] Add indication-tag + safety + identity metadata enrichment notes/script hooks for leaflet corpus in `leaflets/README.md` (no second ingest path; point to 006/017 sole path)
- [X] T070 [P] Architecture review checklist for 020 in `specs/020-pharmacy-recommendation/checklists/architecture-review.md` (016/018/ADR-020-001/frozen API)
- [X] T071 Run and record quickstart drill outcomes in `specs/020-pharmacy-recommendation/quickstart-results.md`
- [X] T072 [P] Update `src/ARCHITECTURE.md` with Pharmacy Recommendation Capability section linking ADR-020-001 and sole-path composition (no new owner)
- [X] T073 [P] Confirm Speckit active pointer remains `specs/020-pharmacy-recommendation/plan.md` in `AGENTS.md`
- [X] T074 Final regression: run unit + architecture 020 tests and fix failures across `tests/unit/services/rag/recommend/`, `tests/unit/fields/pharmacy/`, `tests/architecture/test_020_*.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: Start immediately
- **Phase 2 Foundational**: Depends on Setup — **BLOCKS all user stories**
- **Phase 3 US1 (P1 MVP)**: After Foundational
- **Phase 4 US2 (P1)**: After Foundational; ideally after US1 ranking/decision stubs (shares `recommend/` modules — prefer sequential with US1 on same files)
- **Phase 5 US3 (P2)**: After Foundational; depends on taxonomy confidence from US1
- **Phase 6 US4 (P2)**: After US1 candidate lists exist
- **Phase 7 US5 (P2)**: After Foundational; can parallelize docs with US1 but golden cases richer after US1–US3 behaviors exist
- **Phase 8 US6 (P3)**: After US1–US2 decision/safety paths emit candidates
- **Phase 9 Polish**: After desired stories complete

### User Story Dependencies

| Story | Depends on | Independently testable? |
|-------|------------|-------------------------|
| US1 Need-based recommend | Foundational | Yes (MVP) |
| US2 Safety | Foundational + US1 ranking/decision hooks | Yes with safety fixtures |
| US3 Clarification | Foundational + taxonomy from US1 | Yes with ambiguity fixtures |
| US4 Compare | US1 candidates | Yes on compare fixtures |
| US5 Eval bridge | Foundational (+ richer after US1–US3) | Yes as docs/golden/architecture |
| US6 Trace | US1–US2 outcomes | Yes on diagnostic assertions |

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/pack data before services
- Services before orchestrator wiring
- Answer policy after ranking/decision available
- Story complete before next priority when sharing the same files

### Parallel Opportunities

- Phase 1: T002–T006 [P]
- Phase 2: T008–T009, T011–T012, T014–T015 [P] after T007/T010 sequencing as noted
- US1 tests T017–T020 [P]; pack data T021–T022 [P]
- US2 tests T031–T033 [P]
- US3 tests T040–T042 [P]
- US4 tests T047–T048 [P]
- US5 tests T053–T055 and docs T056–T057, T059 [P]
- US6 tests T061–T063 [P]
- Polish T068–T070, T072–T073 [P]

---

## Parallel Example: User Story 1

```text
# Tests in parallel:
T017 tests/unit/fields/pharmacy/test_symptom_taxonomy.py
T018 tests/unit/services/rag/recommend/test_ranking.py
T019 tests/unit/services/rag/recommend/test_corpus_bounded.py
T020 tests/integration/test_020_recommend_answer_contract.py

# Pack data in parallel:
T021 src/fields/pharmacy/symptom_taxonomy.yaml
T022 src/fields/pharmacy/indication_tags.yaml

# Then sequential implementation:
T023 taxonomy_mapper.py → T024 parser → T025 constraints → T026 ranking → T027 orchestrator → T028–T030
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1)
3. **STOP and VALIDATE** independent test (acidity need → in-corpus ranked answer)
4. Demo via existing `/answer` only

### Incremental Delivery

1. Setup + Foundational
2. US1 MVP (need-based recommend)
3. US2 Safety subset
4. US3 Clarification
5. US4 Compare policy
6. US5 Eval bridge + golden
7. US6 Operator trace
8. Polish + quickstart results

### Parallel Team Strategy

- After Foundational: Dev A = US1/US2 (shared `recommend/`), Dev B = US5 docs/golden, Dev C = architecture tests + US3 taxonomy ambiguity — coordinate on `unified_orchestrator.py` and `parser.py` sequentially

---

## Notes

- `src/services/rag/recommend/` is an **internal helper package** on the sole path — not a new 016 production owner or HTTP service (ADR-020-001)
- Do **not** add `routes/**/recommend*.py` production endpoints
- Do **not** change frozen `/answer` field names
- Ranking weights live only in `recommendation_policy.yaml` (versioned pack)
- Feature 019 owns eval runners; 020 delivers catalog, golden, and bridge docs
- Commit after each task or logical group; mark tasks `[X]` when done during `/speckit-implement`
