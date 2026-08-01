# Tasks: RAG Quality Architecture

**Input**: Design documents from `/specs/018-rag-quality-architecture/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required per constitution (Principle VII) for validation/enforcement behavior. This feature is **architecture-first**: tasks produce ownership maps, continuity registries, review checklists, and architecture tests — **not** retrieval/answer implementation, algorithms, providers, or parallel pipelines (spec Out of Scope; plan Structure Decision; research R1–R14).

**Organization**: Tasks grouped by user story for independent delivery and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5)
- Every task includes an exact file path

## Path Conventions

- Quality architecture artifacts: `specs/018-rag-quality-architecture/governance/`
- Contracts: `specs/018-rag-quality-architecture/contracts/`
- Checklists: `specs/018-rag-quality-architecture/checklists/`
- Platform architecture guide: `src/ARCHITECTURE.md`
- Agent context: `AGENTS.md`
- Tests: `tests/architecture/`
- Offline eval authority (reference only): `specs/014-answer-quality/`
- Ownership baseline (reference only): `specs/016-architecture-consolidation/governance/ownership-registry.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create quality-architecture artifact layout used by all stories.

- [X] T001 Create governance directory scaffold with README in `specs/018-rag-quality-architecture/governance/README.md` describing purpose (quality contracts + continuity registries; not implementation catalog; no algorithms)
- [X] T002 [P] Create empty stage-ownership map stub in `specs/018-rag-quality-architecture/governance/stage-ownership-map.md` with columns Concern | Primary Owner | Secondary Safety-Net | Spec Section | Contract IDs matching `data-model.md` / spec §§1–20
- [X] T003 [P] Create empty continuity-contract index stub in `specs/018-rag-quality-architecture/governance/continuity-contract-index.md` listing C1–C12 with one-line rules from `contracts/quality-continuity.md`
- [X] T004 [P] Create empty quality-entity catalog stub in `specs/018-rag-quality-architecture/governance/quality-entity-catalog.md` listing entities from `data-model.md` (UnderstoodQuery, RetrievalPlan, CandidateLifecycle, EvidencePack, Context, AnswerResult, QualityContext, QualityTrace)
- [X] T005 [P] Create empty vignette catalog stub in `specs/018-rag-quality-architecture/governance/failure-vignette-catalog.md` with columns VignetteId | Symptom | Earliest Broken Contract | Owning Stage
- [X] T006 [P] Add quality-architecture review checklist template in `specs/018-rag-quality-architecture/checklists/quality-architecture-review.md` referencing Contracts C1–C12 and compatibility with 014–017
- [X] T007 [P] Ensure architecture test package exists (reuse) via note in `tests/architecture/README.md` documenting 018 suite markers and how they relate to 016 tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Compatibility freeze + shared quality baseline. **Blocks all user stories.**

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T008 Record “no parallel quality/retrieval/answer path” freeze note in `specs/018-rag-quality-architecture/governance/modularity-freeze.md` citing Contract C8, 016 M0, and `contracts/compatibility.md`
- [X] T009 [P] Confirm Speckit active-plan pointer for 018 in `AGENTS.md` (already planned; verify 018 active blurb + no-implementation-in-plan-phase note remain accurate)
- [X] T010 [P] Add RAG Quality Architecture section (principles summary + link to 018 plan/spec; logical owners only) in `src/ARCHITECTURE.md` without naming package winners or algorithms
- [X] T011 [P] Create quality-metrics catalog stub (architecture-level only) in `specs/018-rag-quality-architecture/governance/stage-quality-metrics.md` from spec §17 — explicitly mark “does not redefine 014 golden metrics”
- [X] T012 [P] Create Quality Context / Trace field registry stub in `specs/018-rag-quality-architecture/governance/quality-context-trace-registry.md` listing Context fields and Trace sections from spec §§16/20 and `contracts/quality-observability.md`
- [X] T013 [P] Create extension-points registry stub in `specs/018-rag-quality-architecture/governance/extension-points-registry.md` from spec §19 with tighten-only rules
- [X] T014 [P] Document relationship “014 = offline authority + feedback; 018 = quality contracts; 015 dual-run transitional; 017 ingest orthogonal” in `specs/018-rag-quality-architecture/governance/relationship-to-014-017.md`
- [X] T015 Add failing/xfail architecture meta-test that 018 governance stubs exist in `tests/architecture/test_018_governance_artifacts_present.py` (assert files under `specs/018-rag-quality-architecture/governance/` exist; content completeness filled by later stories)
- [X] T016 Add scope-guard checklist forbidding algorithms/code/providers/ADRs/sprint impl in `specs/018-rag-quality-architecture/checklists/scope-guard.md` aligned with plan Out of Scope

**Checkpoint**: Foundation ready — ownership maps, continuity indexes, and story validations can proceed.

---

## Phase 3: User Story 1 — Architect Validates Stage Quality Boundaries (Priority: P1) 🎯 MVP

**Goal**: Publish complete stage-ownership map and entity/contract indexes so an architect assigns every §1–20 concern to exactly one primary owner without inventing a new production owner.

**Independent Test**: Reviewer maps all §§1–20 concerns using only `governance/` + `spec.md` + contracts (quickstart §1); `tests/architecture/test_018_stage_ownership_completeness.py` passes.

### Tests for User Story 1

- [X] T017 [P] [US1] Add stage-ownership completeness test in `tests/architecture/test_018_stage_ownership_completeness.py` asserting every concern row in `governance/stage-ownership-map.md` has exactly one Primary Owner and cites a spec section + contract id
- [X] T018 [P] [US1] Add no-new-owner test in `tests/architecture/test_018_no_new_production_owner.py` asserting Primary Owner values are subset of 016 logical parties (Query Understanding, Retrieval Plan, Retrieval, Evidence, Context, Answer Generation, Offline Evaluation, Composition, Domain Packs) — no “Quality Owner”
- [X] T019 [P] [US1] Add entity-catalog coverage test in `tests/architecture/test_018_quality_entity_catalog.py` asserting required entities from `data-model.md` appear in `governance/quality-entity-catalog.md`

### Implementation for User Story 1

- [X] T020 [P] [US1] Fill Query Understanding + Planner + Engine rows (including strategy architecture and full candidate lifecycle steps + score calibration) in `specs/018-rag-quality-architecture/governance/stage-ownership-map.md`
- [X] T021 [P] [US1] Fill Evidence + Context + Answer (incl. logical verification / claim grounding / no-answer) rows in `specs/018-rag-quality-architecture/governance/stage-ownership-map.md`
- [X] T022 [US1] Populate C1–C12 index with normative one-liners and owning contract file links in `specs/018-rag-quality-architecture/governance/continuity-contract-index.md`
- [X] T023 [P] [US1] Populate quality-entity catalog field summaries (no physical type names as normative) in `specs/018-rag-quality-architecture/governance/quality-entity-catalog.md`
- [X] T024 [US1] Publish architect “how to find the quality owner” procedure in `specs/018-rag-quality-architecture/governance/README.md` (registries first; code last; never invent Quality Owner)
- [X] T025 [US1] Cross-link 018 ownership map from `src/ARCHITECTURE.md` RAG Quality section without prescribing source layout

**Checkpoint**: MVP — stage quality boundaries resolvable from docs; US1 architecture tests green.

---

## Phase 4: User Story 2 — Quality Engineer Maps Failures to the Correct Stage (Priority: P1)

**Goal**: Publish failure-vignette catalog and attribution procedure so bad answers map to the earliest broken contract (C1–C12).

**Independent Test**: Blind review of ≥12 vignettes achieves ≥90% correct earliest-contract attribution (quickstart §2); `tests/architecture/test_018_vignette_contract_coverage.py` passes.

### Tests for User Story 2

- [X] T026 [P] [US2] Add vignette catalog structure test in `tests/architecture/test_018_vignette_catalog_structure.py` asserting required columns and ≥12 vignette rows in `governance/failure-vignette-catalog.md`
- [X] T027 [P] [US2] Add vignette→contract coverage test in `tests/architecture/test_018_vignette_contract_coverage.py` asserting every vignette cites a valid C1–C12 id present in `governance/continuity-contract-index.md`
- [X] T028 [P] [US2] Add required vignette themes test in `tests/architecture/test_018_vignette_themes.py` asserting catalog includes filter loss, re-parse drift, false completeness, silent conflict, broken citation, ungrounded claim themes from quickstart §2

### Implementation for User Story 2

- [X] T029 [US2] Author ≥12 failure vignettes with earliest broken contract and owning stage in `specs/018-rag-quality-architecture/governance/failure-vignette-catalog.md`
- [X] T030 [P] [US2] Write quality-engineer attribution procedure (Quality Context/Trace → earliest contract) in `specs/018-rag-quality-architecture/governance/defect-attribution-guide.md`
- [X] T031 [P] [US2] Add defect-attribution checklist in `specs/018-rag-quality-architecture/checklists/defect-attribution.md` for PR/incident review
- [X] T032 [US2] Link vignette catalog + attribution guide from `specs/018-rag-quality-architecture/governance/README.md`
- [X] T033 [P] [US2] Record worked example (partial evidence + budget omission → limited/no-answer) in `specs/018-rag-quality-architecture/governance/continuity-worked-examples.md`

**Checkpoint**: Quality engineers can attribute defects modularly; US2 tests green.

---

## Phase 5: User Story 3 — Product Owner Sees Measurable Quality Outcomes (Priority: P1)

**Goal**: Publish stakeholder-readable outcomes map and stage-metrics catalog proving 014 remains offline authority and success criteria are technology-agnostic.

**Independent Test**: Product owner maps SC-001–SC-010 to user-visible/offline checks without code (quickstart §6–§7); `tests/architecture/test_018_metrics_do_not_redefine_014.py` passes.

### Tests for User Story 3

- [X] T034 [P] [US3] Add metrics non-redefinition test in `tests/architecture/test_018_metrics_do_not_redefine_014.py` asserting `governance/stage-quality-metrics.md` contains explicit “014 authority” language and does not redefine coverage/faithfulness/completeness golden definitions
- [X] T035 [P] [US3] Add success-criteria traceability test in `tests/architecture/test_018_success_criteria_traceability.py` asserting SC-001–SC-010 from `spec.md` each appear in `governance/stakeholder-outcomes.md` with a validation method
- [X] T036 [P] [US3] Add no-answer condition catalog presence test in `tests/architecture/test_018_no_answer_conditions.py` asserting all seven architectural conditions from spec §15 appear in `governance/no-answer-decision-catalog.md`

### Implementation for User Story 3

- [X] T037 [US3] Fill stage-quality metrics catalog (architecture-level) in `specs/018-rag-quality-architecture/governance/stage-quality-metrics.md` from spec §17 with offline-alignment notes only
- [X] T038 [P] [US3] Write stakeholder outcomes map (SC → user-visible behavior → validation drill) in `specs/018-rag-quality-architecture/governance/stakeholder-outcomes.md`
- [X] T039 [P] [US3] Publish no-answer decision catalog (conditions + signal sources + expectations) in `specs/018-rag-quality-architecture/governance/no-answer-decision-catalog.md`
- [X] T040 [P] [US3] Publish claim-level grounding & citation-chain one-pager in `specs/018-rag-quality-architecture/governance/grounding-and-citation-onepager.md` (C5/C12; no algorithms)
- [X] T041 [US3] Document 014 feedback loop (offline → configuration/packs/strategy hints → Composition) in `specs/018-rag-quality-architecture/governance/offline-feedback-loop.md` per `contracts/quality-observability.md`
- [X] T042 [US3] Cross-link 014 as offline authority from `src/ARCHITECTURE.md` RAG Quality section and `governance/relationship-to-014-017.md`

**Checkpoint**: Product-facing quality outcomes and 014 authority are unambiguous; US3 tests green.

---

## Phase 6: User Story 4 — Maintainer Rejects Modularity-Breaking Shortcuts (Priority: P2)

**Goal**: Publish review checklist and anti-shortcut catalog so mega-stages, dual paths, Answer-owned coverage, and runtime-eval owners are rejectable in minutes.

**Independent Test**: Hypothetical dual retrieval path / eval-as-runtime-owner rejected via checklist in <5 minutes (quickstart §3); `tests/architecture/test_018_quality_review_checklist.py` passes.

### Tests for User Story 4

- [X] T043 [P] [US4] Add quality-review checklist structure test in `tests/architecture/test_018_quality_review_checklist.py` asserting `checklists/quality-architecture-review.md` contains MUST reject items for parallel paths, mega-stage merge, Answer-as-coverage-owner, and 014-as-runtime-owner
- [X] T044 [P] [US4] Add modularity freeze documentation test in `tests/architecture/test_018_modularity_freeze.py` asserting `governance/modularity-freeze.md` cites C8 and 016 M0
- [X] T045 [P] [US4] Add compatibility contract presence test in `tests/architecture/test_018_compatibility_contract.py` asserting `contracts/compatibility.md` covers 014/015/016/017 rules referenced by `governance/relationship-to-014-017.md`

### Implementation for User Story 4

- [X] T046 [US4] Complete quality-architecture-review checklist with MUST/MUST NOT items from C8/C10 and `contracts/compatibility.md` in `specs/018-rag-quality-architecture/checklists/quality-architecture-review.md`
- [X] T047 [P] [US4] Create anti-shortcut index (parallel path, mega-stage, coverage-in-Answer, eval-on-request-path, re-parse in Planner) in `specs/018-rag-quality-architecture/governance/anti-shortcut-index.md`
- [X] T048 [US4] Add PR/review process note requiring quality-architecture-review checklist for answer/retrieval quality contract changes in `src/ARCHITECTURE.md`
- [X] T049 [P] [US4] Update `AGENTS.md` Related blurb to require 018 quality-architecture-review (or 016 architecture-review) before accepting parallel quality paths / new quality owners
- [X] T050 [US4] Finalize modularity-freeze wording with rejection examples in `specs/018-rag-quality-architecture/governance/modularity-freeze.md`

**Checkpoint**: Maintainers can reject modularity-breaking “quality shortcuts”; US4 tests green.

---

## Phase 7: User Story 5 — Architect Validates Quality Context and Trace Continuity (Priority: P2)

**Goal**: Publish Quality Context / Trace registries and worked continuity narratives so cumulative quality metadata is reviewable without replacing stage outputs.

**Independent Test**: Reviewer lists Trace sections + producers and walks partial-evidence+budget narrative (quickstart §4); `tests/architecture/test_018_quality_trace_sections.py` passes.

### Tests for User Story 5

- [X] T051 [P] [US5] Add Quality Trace section completeness test in `tests/architecture/test_018_quality_trace_sections.py` asserting all nine Trace sections from spec §16 appear with correct producers in `governance/quality-context-trace-registry.md`
- [X] T052 [P] [US5] Add Quality Context overwrite-rule test in `tests/architecture/test_018_quality_context_rules.py` asserting registry documents additive/namespaced enrichments and forbids upstream overwrite (C11)
- [X] T053 [P] [US5] Add extension-points registry test in `tests/architecture/test_018_extension_points.py` asserting each stage has ≥1 extension point and tighten-only rule is stated in `governance/extension-points-registry.md`

### Implementation for User Story 5

- [X] T054 [US5] Fill Quality Context field registry (ambiguity, retrieval confidence, coverage, conflicts, citations, budget, grounding, degradation history) in `specs/018-rag-quality-architecture/governance/quality-context-trace-registry.md`
- [X] T055 [P] [US5] Fill Quality Trace section registry with required diagnostic contents (degradation, residual filters, sufficiency, budget omissions, grounding outcomes) in `specs/018-rag-quality-architecture/governance/quality-context-trace-registry.md`
- [X] T056 [P] [US5] Fill extension-points registry for all stages in `specs/018-rag-quality-architecture/governance/extension-points-registry.md`
- [X] T057 [US5] Add continuity narrative (partial evidence + disabled rerank + budget conflict omission) to `specs/018-rag-quality-architecture/governance/continuity-worked-examples.md`
- [X] T058 [US5] Cross-link Context/Trace registries from `specs/018-rag-quality-architecture/governance/README.md` and `src/ARCHITECTURE.md`

**Checkpoint**: Quality Context/Trace continuity is docs-complete and test-enforced; US5 tests green.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation of 018 artifacts and docs consistency.

- [X] T059 [P] Execute Architecture Validation scenarios from `specs/018-rag-quality-architecture/quickstart.md` §§1–8 and record results in `specs/018-rag-quality-architecture/governance/quickstart-results.md`
- [X] T060 [P] Verify scope-guard (no algorithms/code/providers/parallel paths absorbed) in `specs/018-rag-quality-architecture/checklists/scope-guard.md`
- [X] T061 Run full 018-related architecture tests under `tests/architecture/test_018_*.py` and fix registry/doc inconsistencies only (no pipeline implementation)
- [X] T062 [P] Sync `specs/018-rag-quality-architecture/checklists/requirements.md` notes with tasks completion status
- [X] T063 Final consistency pass across `AGENTS.md`, `src/ARCHITECTURE.md`, and `specs/018-rag-quality-architecture/governance/*` for sole-owner honesty and 014 offline authority (SC-003/SC-004/SC-010)
- [X] T064 [P] Confirm `contracts/*.md` remain the normative contract sources and governance files only summarize/index them (no divergent rules) via note in `specs/018-rag-quality-architecture/governance/README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Immediate
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all stories**
- **Phase 3 (US1)**: Depends on Phase 2 — MVP
- **Phase 4 (US2)**: Depends on Phase 2; benefits from US1 continuity index
- **Phase 5 (US3)**: Depends on Phase 2; benefits from US1 ownership map
- **Phase 6 (US4)**: Depends on Phase 2; should reference US1–US3 artifacts
- **Phase 7 (US5)**: Depends on Phase 2; benefits from US2 worked examples
- **Phase 8 (Polish)**: Depends on desired stories (recommend all)

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 (P1) | Foundational | Docs-only ownership mapping + architecture tests |
| US2 (P1) | Foundational (+ US1 C1–C12 index preferred) | Vignette attribution + catalog tests |
| US3 (P1) | Foundational (+ US1 map preferred) | Stakeholder outcomes + 014 non-redefinition tests |
| US4 (P2) | Foundational (+ checklists from prior stories) | Review checklist rejects shortcuts |
| US5 (P2) | Foundational (+ US2 examples preferred) | Context/Trace registry tests |

### Parallel Opportunities

- T002–T007 in Setup
- T009–T014 in Foundational
- Within US1: T017–T019 tests; T020–T021 map halves; T023 catalog
- Within US2: T026–T028 tests; T030–T031 docs
- Within US3: T034–T036 tests; T038–T040 docs
- Within US4: T043–T045 tests; T047 docs
- Within US5: T051–T053 tests; T055–T056 registries
- Polish T059/T060/T062/T064

---

## Parallel Example: User Story 1

```text
# Tests in parallel:
Task: T017 tests/architecture/test_018_stage_ownership_completeness.py
Task: T018 tests/architecture/test_018_no_new_production_owner.py
Task: T019 tests/architecture/test_018_quality_entity_catalog.py

# Docs in parallel after tests sketched:
Task: T020 governance/stage-ownership-map.md (QU/Planner/Engine)
Task: T021 governance/stage-ownership-map.md (Evidence/Context/Answer)  # same file — do NOT parallel with T020
Task: T023 governance/quality-entity-catalog.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup  
2. Phase 2 Foundational (modularity freeze + compatibility note)  
3. Phase 3 US1 — publish stage ownership map + contract index  
4. **STOP and VALIDATE** — architect maps §§1–20 without inventing owners  
5. Demo registries + green `tests/architecture/test_018_*` for US1  

### Incremental Delivery

1. US1 → ownership boundaries published  
2. US2 → defect attribution catalog  
3. US3 → stakeholder outcomes + 014 feedback honesty  
4. US4 → standing modularity rejection checklist  
5. US5 → Quality Context/Trace continuity registries  
6. Polish → quickstart results + consistency audit  

### Parallel Team Strategy

- After Foundational: Dev A → US1, Dev B → US2 vignettes/guides, Dev C → US3 outcomes/metrics  
- US4 after US1 checklist links exist  
- US5 can proceed once Context/Trace stubs exist (T012)  

### Explicit Non-Tasks (do not add during execution)

- Implementing retrieval/evidence/context/answer pipeline code  
- Selecting algorithms, formulas, thresholds, or providers  
- Creating a second retrieval or answer path  
- Redefining Feature 014 golden metrics  
- Coupling quality contracts to Feature 017 ingest job lifecycle  
- Physical package/folder “winners”  
- ADRs (out of 018 plan scope)  
- Sprint coding for production cutover  

---

## Notes

- Owner identities are **logical parties** aligned with 016 (e.g. “Canonical Retrieval Owner”), never folder paths
- Verification / claim grounding are logical responsibilities under Answer Generation — never a sixth production owner
- Coverage validation remains Evidence-owned; Answer consumes signals only
- Score calibration remains Engine-owned
- Commit after each task or logical group
- Stop at checkpoints to validate story independence

---

## Task Summary

| Phase | Story | Tasks | Count |
|-------|-------|------:|------:|
| Phase 1 | Setup | T001–T007 | 7 |
| Phase 2 | Foundational | T008–T016 | 9 |
| Phase 3 | US1 | T017–T025 | 9 |
| Phase 4 | US2 | T026–T033 | 8 |
| Phase 5 | US3 | T034–T042 | 9 |
| Phase 6 | US4 | T043–T050 | 8 |
| Phase 7 | US5 | T051–T058 | 8 |
| Phase 8 | Polish | T059–T064 | 6 |
| **Total** | | T001–T064 | **64** |

| Story | Task count | Priority |
|-------|----------:|----------|
| US1 | 9 | P1 (MVP) |
| US2 | 8 | P1 |
| US3 | 9 | P1 |
| US4 | 8 | P2 |
| US5 | 8 | P2 |
| Setup/Foundational/Polish | 22 | — |

### Format validation

- All tasks use `- [ ]`, sequential IDs T001–T064, optional `[P]`, story labels on US phases only, and exact file paths — **confirmed**.
