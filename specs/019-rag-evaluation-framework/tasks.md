# Tasks: RAG Evaluation Framework

**Input**: Design documents from `/specs/019-rag-evaluation-framework/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required per constitution (Principle VII) for validation/enforcement behavior. This feature is **architecture-first**: tasks produce metric-ownership registries, profile/gate maps, governance checklists, experiment/drift catalogs, and architecture tests â€” **not** evaluation runners, scorers, CI YAML, dashboards, algorithms, formulas, thresholds, or parallel production paths (spec Out of Scope; plan Structure Decision; research R1â€“R13).

**Organization**: Tasks grouped by user story for independent delivery and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1â€“US6)
- Every task includes an exact file path

## Path Conventions

- Evaluation architecture artifacts: `specs/019-rag-evaluation-framework/governance/`
- Contracts: `specs/019-rag-evaluation-framework/contracts/`
- Checklists: `specs/019-rag-evaluation-framework/checklists/`
- Platform architecture guide: `src/ARCHITECTURE.md`
- Agent context: `AGENTS.md`
- Tests: `tests/architecture/`
- Offline eval seed (reference only): `specs/014-answer-quality/`
- Quality contracts (reference only): `specs/018-rag-quality-architecture/`
- Ownership baseline (reference only): `specs/016-architecture-consolidation/governance/ownership-registry.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create evaluation-architecture artifact layout used by all stories.

- [X] T001 Create governance directory scaffold with README in `specs/019-rag-evaluation-framework/governance/README.md` describing purpose (evaluation contracts + registries; not implementation catalog; no algorithms/thresholds)
- [X] T002 [P] Create empty metric-ownership registry stub in `specs/019-rag-evaluation-framework/governance/metric-ownership-registry.md` with columns Metric | Primary Owner | Supporting Stages | Blocking vs Diagnostic | Evaluation Scope | Contract Ref matching `contracts/metric-system.md`
- [X] T003 [P] Create empty evaluation-profile index stub in `specs/019-rag-evaluation-framework/governance/evaluation-profile-index.md` listing Smoke/PR/Nightly/Weekly/Release/Shadow/Production Monitoring from `contracts/evaluation-pipeline.md`
- [X] T004 [P] Create empty evaluation-entity catalog stub in `specs/019-rag-evaluation-framework/governance/evaluation-entity-catalog.md` listing entities from `data-model.md` (EvaluationDataset, EvaluationItem, Benchmark, EvaluationProfile, Judge, EvaluationRun, ItemResult, MetricDefinition, CompositeQualityScore, Alert, etc.)
- [X] T005 [P] Create empty error-taxonomy catalog stub in `specs/019-rag-evaluation-framework/governance/error-taxonomy-catalog.md` with the eight categories from `contracts/observability-monitoring.md`
- [X] T006 [P] Add evaluation-architecture review checklist template in `specs/019-rag-evaluation-framework/checklists/evaluation-architecture-review.md` referencing metric ownership, profiles, judges, governance, and compatibility with 014â€“018
- [X] T007 [P] Ensure architecture test package note exists in `tests/architecture/README.md` documenting 019 suite markers and relation to 016/018 architecture tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Compatibility freeze + shared evaluation baseline. **Blocks all user stories.**

**âš  CRITICAL**: No user story work begins until this phase is complete.

- [X] T008 Record â€œevaluation is not a production stage / no parallel answer-retrieval pathâ€ freeze note in `specs/019-rag-evaluation-framework/governance/evaluation-non-ownership-freeze.md` citing 016 M0, research R2, and `contracts/compatibility.md`
- [X] T009 [P] Confirm Speckit active-plan pointer for 019 in `AGENTS.md` (019 active; architecture-only; no-implementation-in-plan-phase note remains accurate)
- [X] T010 [P] Add RAG Evaluation Framework section (principles summary + link to 019 plan/spec; logical owners only) in `src/ARCHITECTURE.md` without naming package winners, formulas, or thresholds
- [X] T011 [P] Create metric-dependency map stub in `specs/019-rag-evaluation-framework/governance/metric-dependency-map.md` from `contracts/metric-system.md` (upstreamâ†’downstream; root-cause annotation does not reassign Primary Owner)
- [X] T012 [P] Create judge-layer registry stub in `specs/019-rag-evaluation-framework/governance/judge-layer-registry.md` listing Rule/LLM/Human/Hybrid + metric-stability rule from `contracts/judge-layer.md`
- [X] T013 [P] Create dataset-benchmark governance summary stub in `specs/019-rag-evaluation-framework/governance/dataset-benchmark-governance-summary.md` covering lifecycle/freeze/lineage/changelog/reproducibility from `contracts/dataset-benchmark-governance.md`
- [X] T014 [P] Document relationship â€œ014 = semantic seed; 019 = evaluation architecture authority; 018 diagnostics; 015 shadow inputs; 016 sole-ownerâ€ in `specs/019-rag-evaluation-framework/governance/relationship-to-014-018.md`
- [X] T015 Add failing/xfail architecture meta-test that 019 governance stubs exist in `tests/architecture/test_019_governance_artifacts_present.py` (assert files under `specs/019-rag-evaluation-framework/governance/` exist; content completeness filled by later stories)
- [X] T016 Add scope-guard checklist forbidding algorithms/formulas/thresholds/code/providers/CI product selection/parallel paths in `specs/019-rag-evaluation-framework/checklists/scope-guard.md` aligned with plan Out of Scope

**Checkpoint**: Foundation ready â€” ownership registries, profile indexes, and story validations can proceed.

---

## Phase 3: User Story 1 â€” Block a Quality Regression on Merge (Priority: P1) ðŸŽ¯ MVP

**Goal**: Publish complete Metric Ownership registry, PR profile/gate binding, and CI-contract summary so a merge regression is attributable to exactly one primary owner per failed metric and fails closed under the PR profile.

**Independent Test**: Reviewer walks quickstart Â§1â€“Â§3 using only `governance/` + `spec.md` + contracts; `tests/architecture/test_019_metric_ownership_completeness.py` passes.

### Tests for User Story 1

- [X] T017 [P] [US1] Add metric-ownership completeness test in `tests/architecture/test_019_metric_ownership_completeness.py` asserting every canonical metric row in `governance/metric-ownership-registry.md` has exactly one Primary Owner and cites `contracts/metric-system.md`
- [X] T018 [P] [US1] Add no-new-production-owner test in `tests/architecture/test_019_no_new_production_owner.py` asserting Primary Owners are subset of 016 logical parties plus Whole Pipeline (ops attribution) / Evaluation system â€” no new production RAG stage owner
- [X] T019 [P] [US1] Add PR-profile freeze requirement test in `tests/architecture/test_019_pr_profile_freeze.py` asserting `governance/evaluation-profile-index.md` requires Frozen Core Golden for PR / PR Core Gate

### Implementation for User Story 1

- [X] T020 [P] [US1] Fill retrieval + planner metric ownership rows (Recall, Precision, MRR, NDCG, Plan Fidelity, Strategy Alignment) in `specs/019-rag-evaluation-framework/governance/metric-ownership-registry.md`
- [X] T021 [P] [US1] Fill answer/citation/safety/ops metric ownership rows (Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate, Latency, Cost) in `specs/019-rag-evaluation-framework/governance/metric-ownership-registry.md`
- [X] T022 [US1] Populate evaluation-profile index for Smoke + PR (dataset tiers, enabled metric sets, gate type, runtime/cost expectation classes â€” no numeric thresholds) in `specs/019-rag-evaluation-framework/governance/evaluation-profile-index.md`
- [X] T023 [P] [US1] Populate metric-dependency map with root-cause annotation rules in `specs/019-rag-evaluation-framework/governance/metric-dependency-map.md`
- [X] T024 [P] [US1] Publish CI contract summary (machine-readable report + fail signal; no secrets/PII in Core Golden) in `specs/019-rag-evaluation-framework/governance/ci-integration-summary.md` from `contracts/evaluation-pipeline.md`
- [X] T025 [US1] Publish â€œhow to attribute a PR gate failureâ€ procedure in `specs/019-rag-evaluation-framework/governance/README.md` (Metric Ownership â†’ Error Taxonomy â†’ Dependency annotation)
- [X] T026 [US1] Cross-link 019 evaluation section from `src/ARCHITECTURE.md` without prescribing source layout or thresholds

**Checkpoint**: MVP â€” PR regression attribution and freeze rules resolvable from docs; US1 architecture tests green.

---

## Phase 4: User Story 2 â€” Score Retrieval Ranking Quality (Priority: P1)

**Goal**: Publish IR metric registry rows, slice dimensions for retrieval, and vignettes so ranking quality is evaluable independent of answer generation with Retrieval Engine as Primary Owner.

**Independent Test**: Reviewer confirms Recall/Precision/MRR/NDCG ownership and a worse-ranking vignette (quickstart Â§2); `tests/architecture/test_019_retrieval_metric_ownership.py` passes.

### Tests for User Story 2

- [X] T027 [P] [US2] Add retrieval metric ownership test in `tests/architecture/test_019_retrieval_metric_ownership.py` asserting Recall/Precision/MRR/NDCG Primary Owner = Retrieval Engine in `governance/metric-ownership-registry.md`
- [X] T028 [P] [US2] Add planner-vs-engine exclusion rule test in `tests/architecture/test_019_planner_constraint_exclusion.py` asserting `governance/metric-dependency-map.md` documents that planner-correct exclusions are not Engine Recall misses
- [X] T029 [P] [US2] Add slice-dimension presence test in `tests/architecture/test_019_slice_dimensions.py` asserting standard dimensions from `contracts/observability-monitoring.md` appear in `governance/slice-dimension-catalog.md`

### Implementation for User Story 2

- [X] T030 [US2] Author â‰¥4 retrieval ranking / miss vignettes with Primary Owner + Error Taxonomy category in `specs/019-rag-evaluation-framework/governance/failure-vignette-catalog.md`
- [X] T031 [P] [US2] Create slice-dimension catalog (domain, language, intent, query complexity, retrieval strategy, planner strategy, document type, tenant, context size, answer length, dataset tier) in `specs/019-rag-evaluation-framework/governance/slice-dimension-catalog.md`
- [X] T032 [P] [US2] Document IR evaluation scope (offline primary; online proxy optional) in `specs/019-rag-evaluation-framework/governance/retrieval-evaluation-notes.md`
- [X] T033 [US2] Link retrieval notes + vignettes from `specs/019-rag-evaluation-framework/governance/README.md`

**Checkpoint**: Retrieval ranking quality is attributable without answer generation; US2 tests green.

---

## Phase 5: User Story 3 â€” Detect Hallucinations and Bad Citations (Priority: P1)

**Goal**: Publish hallucination/citation ownership, judge-stability rules, and adversarial vignettes so fabricated claims and mismatched citations fail under Answer Generation ownership with stable metric identities across judges.

**Independent Test**: Reviewer walks quickstart Â§5; `tests/architecture/test_019_judge_metric_stability.py` and hallucination vignette tests pass.

### Tests for User Story 3

- [X] T034 [P] [US3] Add answer-safety ownership test in `tests/architecture/test_019_answer_safety_ownership.py` asserting Faithfulness/Groundedness/Citation Accuracy/Hallucination Rate Primary Owner = Answer Generation
- [X] T035 [P] [US3] Add judge metric-stability test in `tests/architecture/test_019_judge_metric_stability.py` asserting `governance/judge-layer-registry.md` forbids judge-specific parallel metric names
- [X] T036 [P] [US3] Add adversarial vignette theme test in `tests/architecture/test_019_adversarial_vignette_themes.py` asserting fabricated-entity, mismatched-citation, and correct-no-answer themes exist in `governance/failure-vignette-catalog.md`

### Implementation for User Story 3

- [X] T037 [US3] Fill judge-layer registry (Rule/LLM/Human/Hybrid, provenance, Hybrid precedence policy shape) in `specs/019-rag-evaluation-framework/governance/judge-layer-registry.md`
- [X] T038 [P] [US3] Document optional Metric Confidence fields (confidence, judge version, agreement, provenance) in `specs/019-rag-evaluation-framework/governance/metric-confidence-notes.md` from `contracts/metric-system.md`
- [X] T039 [US3] Author â‰¥5 adversarial/citation/hallucination vignettes with Error Taxonomy (Grounding/Citation/Generation) in `specs/019-rag-evaluation-framework/governance/failure-vignette-catalog.md`
- [X] T040 [P] [US3] Complete error-taxonomy catalog with reporting rules (no silent PASS for Evaluation/Infrastructure Failure) in `specs/019-rag-evaluation-framework/governance/error-taxonomy-catalog.md`
- [X] T041 [US3] Link judge + confidence + adversarial notes from `specs/019-rag-evaluation-framework/governance/README.md`

**Checkpoint**: Hallucination/citation failures are attributable and judge-stable; US3 tests green.

---

## Phase 6: User Story 4 â€” Evaluate Planner Decisions (Priority: P2)

**Goal**: Publish planner metric ownership and vignettes so Plan Fidelity / Strategy Alignment failures attribute to Retrieval Planner without blaming Engine ranking.

**Independent Test**: Reviewer walks quickstart planner scenarios; `tests/architecture/test_019_planner_metric_ownership.py` passes.

### Tests for User Story 4

- [X] T042 [P] [US4] Add planner metric ownership test in `tests/architecture/test_019_planner_metric_ownership.py` asserting Plan Fidelity / Strategy Alignment Primary Owner = Retrieval Planner
- [X] T043 [P] [US4] Add re-parse-as-planner-failure note test in `tests/architecture/test_019_planner_reparse_rule.py` asserting `governance/planner-evaluation-notes.md` cites 018 Understood Query authority / no re-parse
- [X] T044 [P] [US4] Add planner vignette theme test in `tests/architecture/test_019_planner_vignette_themes.py` asserting omitted-constraint and re-parse themes exist in `governance/failure-vignette-catalog.md`

### Implementation for User Story 4

- [X] T045 [US4] Publish planner evaluation notes (labels required, Engine not credited for plan quality) in `specs/019-rag-evaluation-framework/governance/planner-evaluation-notes.md`
- [X] T046 [P] [US4] Author â‰¥3 planner failure vignettes with Planner Failure taxonomy in `specs/019-rag-evaluation-framework/governance/failure-vignette-catalog.md`
- [X] T047 [US4] Cross-link planner notes from `specs/019-rag-evaluation-framework/governance/metric-ownership-registry.md` and `governance/README.md`

**Checkpoint**: Planner defects separable from Engine ranking; US4 tests green.

---

## Phase 7: User Story 5 â€” Compare Offline Benchmark Runs Across Releases (Priority: P2)

**Goal**: Publish experiment roles, benchmark governance summary, composite-score purpose notes, and run-metadata checklist so Champion/Challenger diffs are comparable on frozen benchmark versions.

**Independent Test**: Reviewer walks quickstart Â§4 and Â§6; `tests/architecture/test_019_experiment_roles.py` and benchmark freeze tests pass.

### Tests for User Story 5

- [X] T048 [P] [US5] Add experiment-role completeness test in `tests/architecture/test_019_experiment_roles.py` asserting Baseline/Candidate/Champion/Challenger/Shadow/Canary appear in `governance/experiment-role-catalog.md`
- [X] T049 [P] [US5] Add benchmark freeze rule test in `tests/architecture/test_019_benchmark_freeze.py` asserting `governance/dataset-benchmark-governance-summary.md` forbids in-place mutation of Frozen benchmarks
- [X] T050 [P] [US5] Add run-metadata field coverage test in `tests/architecture/test_019_run_metadata_fields.py` asserting commit/branch/release/component versions/fingerprint fields from `data-model.md` appear in `governance/evaluation-run-metadata-catalog.md`

### Implementation for User Story 5

- [X] T051 [US5] Fill dataset-benchmark governance summary (lifecycle, approval, freeze, retirement, lineage, changelog, reproducibility, responsibilities) in `specs/019-rag-evaluation-framework/governance/dataset-benchmark-governance-summary.md`
- [X] T052 [P] [US5] Create experiment-role catalog with comparison rules (no deployment mechanics) in `specs/019-rag-evaluation-framework/governance/experiment-role-catalog.md` from `contracts/experiment-comparison.md`
- [X] T053 [P] [US5] Create evaluation-run-metadata catalog in `specs/019-rag-evaluation-framework/governance/evaluation-run-metadata-catalog.md`
- [X] T054 [P] [US5] Document composite quality scores as derived views with drill-down (no formulas) in `specs/019-rag-evaluation-framework/governance/composite-score-catalog.md`
- [X] T055 [US5] Populate Nightly/Weekly/Release rows in `specs/019-rag-evaluation-framework/governance/evaluation-profile-index.md`
- [X] T056 [US5] Link experiment/benchmark/run-metadata catalogs from `specs/019-rag-evaluation-framework/governance/README.md`

**Checkpoint**: Release comparisons are freeze/version honest; US5 tests green.

---

## Phase 8: User Story 6 â€” Observe Production Drift and Ops Health (Priority: P3)

**Goal**: Publish drift taxonomy, alert categories, monitoring view index, and Shadow/Production Monitoring profile rows so operators distinguish alerts from gates and offline authority remains primary for merge.

**Independent Test**: Reviewer walks quickstart Â§7; `tests/architecture/test_019_drift_and_alerts.py` passes.

### Tests for User Story 6

- [X] T057 [P] [US6] Add drift-taxonomy completeness test in `tests/architecture/test_019_drift_taxonomy.py` asserting eight drift categories in `governance/drift-taxonomy-catalog.md`
- [X] T058 [P] [US6] Add alert-vs-gate rule test in `tests/architecture/test_019_alerts_vs_gates.py` asserting `governance/alert-catalog.md` states alerts notify / gates decide
- [X] T059 [P] [US6] Add monitoring-view presence test in `tests/architecture/test_019_monitoring_views.py` asserting required views from `contracts/observability-monitoring.md` appear in `governance/monitoring-view-index.md`

### Implementation for User Story 6

- [X] T060 [US6] Fill drift-taxonomy catalog with offline-authority relationship in `specs/019-rag-evaluation-framework/governance/drift-taxonomy-catalog.md`
- [X] T061 [P] [US6] Create alert catalog (Threshold/Regression/Trend/Drift/Cost/Latency) in `specs/019-rag-evaluation-framework/governance/alert-catalog.md`
- [X] T062 [P] [US6] Create monitoring-view index (Quality/Retrieval/Planner/Ops/Gate Status/Defect Hotspots/Drift Board/Experiment Board) in `specs/019-rag-evaluation-framework/governance/monitoring-view-index.md`
- [X] T063 [US6] Populate Shadow + Production Monitoring rows in `specs/019-rag-evaluation-framework/governance/evaluation-profile-index.md`
- [X] T064 [P] [US6] Document evaluation lifecycle loop (Datasetâ†’â€¦â†’Dataset Evolution) in `specs/019-rag-evaluation-framework/governance/evaluation-lifecycle.md`
- [X] T065 [US6] Link monitoring/drift/alert/lifecycle docs from `specs/019-rag-evaluation-framework/governance/README.md` and `src/ARCHITECTURE.md`

**Checkpoint**: Production drift/ops health is observable without request-path ownership; US6 tests green.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation of 019 artifacts and docs consistency.

- [X] T066 [P] Execute Architecture Validation scenarios from `specs/019-rag-evaluation-framework/quickstart.md` Â§Â§1â€“9 and record results in `specs/019-rag-evaluation-framework/governance/quickstart-results.md`
- [X] T067 [P] Verify scope-guard (no algorithms/thresholds/code/providers/parallel paths absorbed) in `specs/019-rag-evaluation-framework/checklists/scope-guard.md`
- [X] T068 Run full 019-related architecture tests under `tests/architecture/test_019_*.py` and fix registry/doc inconsistencies only (no evaluation implementation)
- [X] T069 [P] Complete evaluation-architecture-review checklist MUST/MUST NOT items in `specs/019-rag-evaluation-framework/checklists/evaluation-architecture-review.md`
- [X] T070 [P] Sync `specs/019-rag-evaluation-framework/checklists/requirements.md` notes with tasks completion status
- [X] T071 [P] Document Future Evaluation Extensions as non-scope placeholders in `specs/019-rag-evaluation-framework/governance/future-extension-points.md` from spec Future section
- [X] T072 Final consistency pass across `AGENTS.md`, `src/ARCHITECTURE.md`, and `specs/019-rag-evaluation-framework/governance/*` for sole-owner honesty, 014 semantic continuity, and 019 gate precedence over 018 diagnostics (SC-011/SC-012)
- [X] T073 [P] Confirm `contracts/*.md` remain the normative contract sources and governance files only summarize/index them (no divergent rules) via note in `specs/019-rag-evaluation-framework/governance/README.md`
- [X] T074 [P] Populate evaluation-entity catalog field summaries (no physical type names as normative) in `specs/019-rag-evaluation-framework/governance/evaluation-entity-catalog.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Immediate
- **Phase 2 (Foundational)**: Depends on Phase 1 â€” **blocks all stories**
- **Phase 3 (US1)**: Depends on Phase 2 â€” MVP
- **Phase 4 (US2)**: Depends on Phase 2; benefits from US1 ownership registry
- **Phase 5 (US3)**: Depends on Phase 2; benefits from US1 ownership + judge stub (T012)
- **Phase 6 (US4)**: Depends on Phase 2; benefits from US1/US2 ownership + dependency map
- **Phase 7 (US5)**: Depends on Phase 2; benefits from profile index + governance stubs
- **Phase 8 (US6)**: Depends on Phase 2; benefits from US5 profile/experiment catalogs
- **Phase 9 (Polish)**: Depends on desired stories (recommend all)

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 (P1) | Foundational | PR ownership + freeze + CI summary + architecture tests |
| US2 (P1) | Foundational (+ US1 registry preferred) | IR ownership + ranking vignettes |
| US3 (P1) | Foundational (+ judge stub) | Safety ownership + judge stability + adversarial vignettes |
| US4 (P2) | Foundational (+ US1/US2 preferred) | Planner ownership + vignettes |
| US5 (P2) | Foundational (+ governance stubs) | Experiment roles + freeze + run metadata |
| US6 (P3) | Foundational (+ US5 profiles preferred) | Drift/alert/monitoring views |

### Parallel Opportunities

- T002â€“T007 in Setup
- T009â€“T014 in Foundational
- Within US1: T017â€“T019 tests; T020â€“T021 ownership halves; T023â€“T024 docs
- Within US2: T027â€“T029 tests; T031â€“T032 docs
- Within US3: T034â€“T036 tests; T038/T040 docs
- Within US4: T042â€“T044 tests; T046 vignettes
- Within US5: T048â€“T050 tests; T052â€“T054 catalogs
- Within US6: T057â€“T059 tests; T061â€“T062/T064 docs
- Polish T066/T067/T069â€“T071/T073â€“T074

---

## Parallel Example: User Story 1

```text
# Tests in parallel:
Task: T017 tests/architecture/test_019_metric_ownership_completeness.py
Task: T018 tests/architecture/test_019_no_new_production_owner.py
Task: T019 tests/architecture/test_019_pr_profile_freeze.py

# Docs in parallel after tests sketched:
Task: T020 governance/metric-ownership-registry.md (retrieval/planner)
Task: T021 governance/metric-ownership-registry.md (answer/ops)  # same file â€” do NOT parallel with T020
Task: T023 governance/metric-dependency-map.md
Task: T024 governance/ci-integration-summary.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup  
2. Phase 2 Foundational (non-ownership freeze + compatibility note)  
3. Phase 3 US1 â€” publish metric ownership + PR profile/CI summary  
4. **STOP and VALIDATE** â€” reviewer attributes a synthetic PR gate failure without inventing owners  
5. Demo registries + green `tests/architecture/test_019_*` for US1  

### Incremental Delivery

1. US1 â†’ merge regression attribution published  
2. US2 â†’ retrieval IR ownership + vignettes  
3. US3 â†’ hallucination/citation + judge stability  
4. US4 â†’ planner evaluation separation  
5. US5 â†’ benchmark/experiment/run-metadata comparability  
6. US6 â†’ drift/alerts/monitoring views  
7. Polish â†’ quickstart results + consistency audit  

### Parallel Team Strategy

- After Foundational: Dev A â†’ US1, Dev B â†’ US2 vignettes/slices, Dev C â†’ US3 judge/adversarial  
- US4 after US1 dependency map exists  
- US5/US6 after profile/governance stubs exist  

### Explicit Non-Tasks (do not add during execution)

- Implementing evaluation runners, scorers, or judge engines  
- Selecting algorithms, formulas, numeric thresholds, or providers  
- Writing CI workflow YAML or choosing CI/dashboard vendors  
- Creating a second retrieval or answer path / request-path evaluation  
- Redefining Feature 014 Faithfulness/Completeness semantics  
- Reassigning Feature 016 sole owners or adding a production â€œEvaluationâ€ stage  
- Coupling evaluation contracts to Feature 017 ingest job lifecycle  
- Physical package/folder â€œwinnersâ€  
- ADRs (out of 019 plan scope unless separately authorized)  
- Implementing Future Evaluation Extensions (multimodal/agent/etc.)  

---

## Notes

- Owner identities are **logical parties** aligned with 016 (e.g. â€œRetrieval Engineâ€), never folder paths
- Whole Pipeline (ops attribution) for Latency/Cost is evaluation attribution only â€” never a new 016 sole owner
- 019 gates win over 018 diagnostics for release decisions; 014 metric semantics remain continuous
- Commit after each task or logical group
- Stop at checkpoints to validate story independence

---

## Task Summary

| Phase | Story | Tasks | Count |
|-------|-------|------:|------:|
| Phase 1 | Setup | T001â€“T007 | 7 |
| Phase 2 | Foundational | T008â€“T016 | 9 |
| Phase 3 | US1 | T017â€“T026 | 10 |
| Phase 4 | US2 | T027â€“T033 | 7 |
| Phase 5 | US3 | T034â€“T041 | 8 |
| Phase 6 | US4 | T042â€“T047 | 6 |
| Phase 7 | US5 | T048â€“T056 | 9 |
| Phase 8 | US6 | T057â€“T065 | 9 |
| Phase 9 | Polish | T066â€“T074 | 9 |
| **Total** | | T001â€“T074 | **74** |

| Story | Task count | Priority |
|-------|----------:|----------|
| US1 | 10 | P1 (MVP) |
| US2 | 7 | P1 |
| US3 | 8 | P1 |
| US4 | 6 | P2 |
| US5 | 9 | P2 |
| US6 | 9 | P3 |
| Setup/Foundational/Polish | 25 | â€” |

### Format validation

- All tasks use `- [X]` (completed), sequential IDs T001â€“T074, optional `[P]`, story labels on US phases only, and exact file paths â€” **confirmed**.
)

