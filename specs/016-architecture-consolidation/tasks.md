# Tasks: Architecture Consolidation

**Input**: Design documents from `/specs/016-architecture-consolidation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required per constitution (Principle VII) for validation/enforcement behavior. This feature is governance-first: tasks produce registries, review gates, validation tests, and migration runbooks — **not** package-winner prescriptions (spec AP12/AP14, research R-001).

**Organization**: Tasks grouped by user story for independent delivery and testing.

**Setup note**: `setup-tasks.ps1 -Json` could not run (shell allowlist). Paths resolved from `.specify/feature.json`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US4)
- Every task includes an exact file path

## Path Conventions

- Governance artifacts: `specs/016-architecture-consolidation/governance/`
- Platform architecture guide: `src/ARCHITECTURE.md`
- Agent context: `AGENTS.md`
- Tests: `tests/architecture/`, `tests/contract/`, `tests/integration/`
- Review templates: `specs/016-architecture-consolidation/checklists/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create governance artifact layout used by all stories.

- [X] T001 Create governance directory scaffold with README in `specs/016-architecture-consolidation/governance/README.md` describing purpose (rules + registries; not component catalog)
- [X] T002 [P] Create empty ownership registry stub in `specs/016-architecture-consolidation/governance/ownership-registry.md` matching `OwnershipBinding` fields from `data-model.md`
- [X] T003 [P] Create empty lifecycle registry stub in `specs/016-architecture-consolidation/governance/lifecycle-registry.md` using lifecycle vocabulary from `contracts/lifecycle.md`
- [X] T004 [P] Create empty contract-role catalog stub in `specs/016-architecture-consolidation/governance/contract-role-catalog.md` listing ContractRole names from `data-model.md`
- [X] T005 [P] Create architecture test package init in `tests/architecture/__init__.py`
- [X] T006 [P] Add architecture-review checklist template in `specs/016-architecture-consolidation/checklists/architecture-review.md` referencing Principles, Invariants, and Anti-Patterns from `spec.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: M0 freeze + shared governance baseline. **Blocks all user stories.**

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T007 Record dual-path growth freeze (M0) in `specs/016-architecture-consolidation/governance/m0-freeze.md` stating no new parallel production implementations without ADR
- [X] T008 [P] Update Speckit active-plan pointer and freeze notice in `AGENTS.md` (016 active; dual-path transitional; no new parallel paths)
- [X] T009 [P] Add consolidation governance section (principles summary + link to 016) in `src/ARCHITECTURE.md` without naming package winners
- [X] T010 [P] Create ADR index linking ADR-001…004 in `specs/016-architecture-consolidation/governance/adr-index.md`
- [X] T011 [P] Create capability card working doc skeleton (Answer/Ingest/Search/Offline Evaluation) in `specs/016-architecture-consolidation/governance/capability-cards.md` with Purpose/Concerns/Contracts/Ownership/Allowed/Forbidden columns from `spec.md`
- [X] T012 [P] Create Owner Selection worksheet template in `specs/016-architecture-consolidation/governance/owner-selection-worksheet.md` with select-by / never-by criteria from `spec.md`
- [X] T013 [P] Create pytest markers/docs note for architecture suite in `tests/architecture/README.md` (how to run; maps to Validation categories)
- [X] T014 Add failing architecture meta-test that registries exist and are non-empty after fill phases in `tests/architecture/test_governance_artifacts_present.py` (assert files under `specs/016-architecture-consolidation/governance/` exist; skip content completeness until US1 fills them, or use xfail/markers as appropriate)
- [X] T015 Document relationship “015 = cutover vehicle, 016 = governance target” in `specs/016-architecture-consolidation/governance/relationship-to-015.md`

**Checkpoint**: Foundation ready — ownership publication and migration gates can proceed.

---

## Phase 3: User Story 1 — Architect Resolves Ownership Without Reading Code (Priority: P1) 🎯 MVP

**Goal**: Publish capability cards, ownership bindings, and contract roles so an architect can determine ownership from docs alone.

**Independent Test**: Reviewer answers Owner/Consumers/lifecycle for Answer and Ingest concerns using only `governance/` + `spec.md` (quickstart §1); `tests/architecture/test_ownership_completeness.py` passes.

### Tests for User Story 1

- [X] T016 [P] [US1] Add ownership completeness test in `tests/architecture/test_ownership_completeness.py` asserting every production concern listed in `governance/capability-cards.md` has exactly one Owner row in `governance/ownership-registry.md`
- [X] T017 [P] [US1] Add contract-role uniqueness test in `tests/architecture/test_contract_role_uniqueness.py` asserting one canonical role per concept in `governance/contract-role-catalog.md`
- [X] T018 [P] [US1] Add decision traceability test in `tests/architecture/test_decision_traceability.py` asserting each Architecture Decision id in `spec.md` maps to an ADR or Principle/Invariant per `governance/adr-index.md`

### Implementation for User Story 1

- [X] T019 [P] [US1] Fill Answer and Ingest capability cards in `specs/016-architecture-consolidation/governance/capability-cards.md` from `spec.md` Canonical Architecture
- [X] T020 [P] [US1] Fill Search and Offline Evaluation capability cards in `specs/016-architecture-consolidation/governance/capability-cards.md`
- [X] T021 [US1] Populate logical OwnershipBindings (Owner/Contributors/Consumers) for all Required Concerns in `specs/016-architecture-consolidation/governance/ownership-registry.md` using Owner Selection Criteria — **do not** use folder/package names as owner identity
- [X] T022 [P] [US1] Populate ContractRole catalog entries for shared concepts in `specs/016-architecture-consolidation/governance/contract-role-catalog.md`
- [X] T023 [P] [US1] Record lifecycle states for known non-production capabilities (at minimum structured knowledge per ADR-004) in `specs/016-architecture-consolidation/governance/lifecycle-registry.md`
- [X] T024 [US1] Publish architect-facing summary linking registries in `src/ARCHITECTURE.md` (canonical map section) without prescribing source layout
- [X] T025 [US1] Add “how to find the owner” procedure in `specs/016-architecture-consolidation/governance/README.md` pointing to registries first, code last

**Checkpoint**: MVP — ownership resolvable from docs; US1 architecture tests green.

---

## Phase 4: User Story 2 — Maintainer Retires Parallel Paths Safely (Priority: P1)

**Goal**: Migration runbook, retirement gates, and rollback procedure so Retire After Cutover cannot precede sole ownership.

**Independent Test**: For a sample Retire After Cutover concern, runbook shows predecessor phase + gate; rollback drill doc exists; `tests/architecture/test_migration_phase_order.py` passes (quickstart §6–§9).

### Tests for User Story 2

- [X] T026 [P] [US2] Add migration phase-order test in `tests/architecture/test_migration_phase_order.py` parsing `governance/migration-runbook.md` to assert retirement phases require prior sole-owner phases (P11)
- [X] T027 [P] [US2] Add lifecycle honesty test in `tests/architecture/test_lifecycle_honesty.py` asserting `AGENTS.md` / `src/ARCHITECTURE.md` do not claim production-complete status for Activation Pending / Dormant / Research entries in `governance/lifecycle-registry.md`
- [X] T028 [P] [US2] Ensure frozen answer API contract test remains present/green in `tests/contract/test_answer_api.py` per `contracts/api-stability.md` (extend only if coverage gaps vs 015 freeze)

### Implementation for User Story 2

- [X] T029 [US2] Write migration runbook for M0–M8 outcomes and exit gates in `specs/016-architecture-consolidation/governance/migration-runbook.md` aligned with `plan.md` and `quickstart.md`
- [X] T030 [P] [US2] Write retirement checklist in `specs/016-architecture-consolidation/checklists/retirement-gate.md` (sole owner, zero consumers, rollback verified, diagnostics not hidden)
- [X] T031 [P] [US2] Write rollback drill procedure (pre-M7) in `specs/016-architecture-consolidation/governance/rollback-drill.md`
- [X] T032 [P] [US2] Document Search interim retrieval ownership explicitly in `specs/016-architecture-consolidation/governance/search-interim-ownership.md` (ADR-002; forbid undocumented divergence)
- [X] T033 [US2] Add M1 Answer sole-owner gate checklist linking 015 cutover vehicle in `specs/016-architecture-consolidation/checklists/m1-answer-sole-owner.md`
- [X] T034 [P] [US2] Add M2/M4 gate checklists for retrieval and ingest/chunking sole ownership in `specs/016-architecture-consolidation/checklists/m2-retrieval-sole-owner.md` and `specs/016-architecture-consolidation/checklists/m4-ingest-chunking-sole-owner.md`
- [X] T035 [US2] Record re-index / waiver policy for embed-text unification in `specs/016-architecture-consolidation/governance/reindex-compatibility.md` (research R-010)
- [X] T036 [US2] Mark competitor concerns as Consolidate / Retire After Cutover in `specs/016-architecture-consolidation/governance/lifecycle-registry.md` without selecting physical package survivors

**Checkpoint**: Maintainers can gate retirement safely; US2 tests green.

---

## Phase 5: User Story 3 — Domain Author Extends Without Capturing Core (Priority: P1)

**Goal**: Domain Packs own vertical heuristics; core orchestration ownership unchanged when packs change.

**Independent Test**: Pack extension guide shows zero required core-ownership edits; domain-leakage inventory has disposition; `tests/architecture/test_domain_pack_ownership_rules.py` passes.

### Tests for User Story 3

- [X] T037 [P] [US3] Add domain-pack ownership rules test in `tests/architecture/test_domain_pack_ownership_rules.py` asserting Domain Packs are Owner of domain vocabulary rows and not Owner of core orchestration rows in `governance/ownership-registry.md`
- [X] T038 [P] [US3] Add anti-pattern AP5 documentation test in `tests/architecture/test_forbidden_patterns_documented.py` asserting Composition must not own domain heuristics per `governance/capability-cards.md` / ownership registry

### Implementation for User Story 3

- [X] T039 [US3] Create domain extension guide for pack authors in `specs/016-architecture-consolidation/governance/domain-pack-extension-guide.md` (reuse contracts; no core control-flow edits)
- [X] T040 [P] [US3] Create domain-leakage inventory template and initial findings log in `specs/016-architecture-consolidation/governance/domain-leakage-inventory.md` (concern-level findings; disposition = Consolidate Into Domain Packs)
- [X] T041 [US3] Update ownership registry so vertical heuristics concerns list Domain Packs as Owner in `specs/016-architecture-consolidation/governance/ownership-registry.md`
- [X] T042 [P] [US3] Add M6 domain-extraction gate checklist in `specs/016-architecture-consolidation/checklists/m6-domain-extraction.md`
- [X] T043 [US3] Cross-link field-registry / packs docs from `src/ARCHITECTURE.md` to `governance/domain-pack-extension-guide.md` without encoding a vertical into core

**Checkpoint**: Domain authors have a pack-first path; US3 tests green.

---

## Phase 6: User Story 4 — Governance Prevents Future Drift (Priority: P2)

**Goal**: Future changes are accept/rejectable via Governance + Anti-Patterns without reopening consolidation.

**Independent Test**: Hypothetical parallel retrieval path rejected using checklist in <5 minutes; `tests/architecture/test_governance_review_checklist.py` passes (quickstart §2).

### Tests for User Story 4

- [X] T044 [P] [US4] Add governance checklist presence/structure test in `tests/architecture/test_governance_review_checklist.py` validating `checklists/architecture-review.md` contains required MUST items from `contracts/governance.md`
- [X] T045 [P] [US4] Add forbidden-pattern coverage test in `tests/architecture/test_antipattern_coverage.py` asserting AP1–AP14 are listed in `checklists/architecture-review.md` or `governance/antipattern-index.md`

### Implementation for User Story 4

- [X] T046 [P] [US4] Complete architecture-review checklist with Governance MUST/MUST NOT items in `specs/016-architecture-consolidation/checklists/architecture-review.md`
- [X] T047 [P] [US4] Create anti-pattern index (AP1–AP14) with supersession rules in `specs/016-architecture-consolidation/governance/antipattern-index.md`
- [X] T048 [US4] Add PR/review process section requiring architecture-review checklist for capability changes in `src/ARCHITECTURE.md`
- [X] T049 [P] [US4] Document exception-ADR requirements (scope/duration/exit) in `specs/016-architecture-consolidation/governance/exception-adr-template.md`
- [X] T050 [US4] Update `AGENTS.md` Related blurb to require governance checklist for new parallel paths / ownership changes
- [X] T051 [US4] Add M7/M8 polish checklists for retirement wave and lifecycle resolution in `specs/016-architecture-consolidation/checklists/m7-retirement-wave.md` and `specs/016-architecture-consolidation/checklists/m8-lifecycle-resolution.md`

**Checkpoint**: Drift proposals rejectable via published governance; US4 tests green.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation of 016 artifacts and docs consistency.

- [X] T052 [P] Execute Architecture Validation scenarios from `specs/016-architecture-consolidation/quickstart.md` §§1–6 and record results in `specs/016-architecture-consolidation/governance/quickstart-results.md`
- [X] T053 [P] Verify Out of Scope guard (no perf/API/DB redesign absorbed) in `specs/016-architecture-consolidation/checklists/scope-guard.md`
- [X] T054 Run full architecture test suite under `tests/architecture/` and fix registry/doc inconsistencies only (no package-winner changes)
- [X] T055 [P] Sync `specs/016-architecture-consolidation/checklists/requirements.md` notes with tasks completion status
- [X] T056 Final consistency pass across `AGENTS.md`, `src/ARCHITECTURE.md`, and `specs/016-architecture-consolidation/governance/*` for lifecycle honesty (SC-011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Immediate
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all stories**
- **Phase 3 (US1)**: Depends on Phase 2 — MVP
- **Phase 4 (US2)**: Depends on Phase 2; benefits from US1 registries (ownership/lifecycle rows) but independently testable via runbook/gate docs
- **Phase 5 (US3)**: Depends on Phase 2; should use US1 ownership registry structure
- **Phase 6 (US4)**: Depends on Phase 2; should reference US1–US3 artifacts
- **Phase 7 (Polish)**: Depends on desired stories (recommend all)

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 (P1) | Foundational | Docs-only ownership resolution + architecture tests |
| US2 (P1) | Foundational (+ US1 registries preferred) | Runbook/gate order tests + rollback doc |
| US3 (P1) | Foundational (+ US1 ownership registry) | Pack guide + ownership rules tests |
| US4 (P2) | Foundational (+ checklists from prior stories) | Review checklist rejects parallel path |

### Parallel Opportunities

- T002–T006 in Setup
- T008–T013 in Foundational
- Within US1: T016–T018 tests; T019–T020 cards; T022–T023 catalogs
- Within US2: T026–T028 tests; T030–T032 docs
- Within US3: T037–T038 tests; T040/T042
- Within US4: T044–T045 tests; T046–T047/T049
- Polish T052/T053/T055

---

## Parallel Example: User Story 1

```text
# Tests in parallel:
Task: T016 tests/architecture/test_ownership_completeness.py
Task: T017 tests/architecture/test_contract_role_uniqueness.py
Task: T018 tests/architecture/test_decision_traceability.py

# Docs in parallel after tests sketched:
Task: T019 capability-cards.md (Answer/Ingest)
Task: T020 capability-cards.md (Search/Offline Evaluation)  # same file — do NOT parallel with T019
Task: T022 contract-role-catalog.md
Task: T023 lifecycle-registry.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup  
2. Phase 2 Foundational (M0 freeze)  
3. Phase 3 US1 — publish ownership/contracts  
4. **STOP and VALIDATE** — architect resolves ownership without code  
5. Demo registries + green `tests/architecture/` for US1  

### Incremental Delivery

1. US1 → ownership map exists  
2. US2 → safe retirement/migration gates  
3. US3 → domain pack extension path  
4. US4 → standing drift prevention  
5. Polish → quickstart results + honesty audit  

### Parallel Team Strategy

- After Foundational: Dev A → US1, Dev B → US2 runbook/checklists (coordinate on `lifecycle-registry.md`), Dev C → US3 guide/inventory  
- US4 after US1 checklist links exist  

### Explicit Non-Tasks (do not add during execution)

- Selecting physical package “winners” by age/folder name  
- Retrieval/quality algorithm changes  
- API redesign  
- Implementation cutover coding already owned by 015 (reuse as vehicle)  
- Performance optimization programs  

---

## Notes

- Owner identities in registries are **logical parties** (e.g. “Canonical Retrieval Owner”), never folder paths
- Physical module mapping, if needed later, belongs in implementation docs after Owner Selection worksheets — not as silent task scope expansion
- 015 remains the answer cutover mechanism; 016 tasks gate and govern
- Commit after each task or logical group
- Stop at checkpoints to validate story independence

---

## Task Summary

| Phase | Story | Tasks | Count |
|-------|-------|-------|------:|
| Phase 1 | Setup | T001–T006 | 6 |
| Phase 2 | Foundational | T007–T015 | 9 |
| Phase 3 | US1 | T016–T025 | 10 |
| Phase 4 | US2 | T026–T036 | 11 |
| Phase 5 | US3 | T037–T043 | 7 |
| Phase 6 | US4 | T044–T051 | 8 |
| Phase 7 | Polish | T052–T056 | 5 |
| **Total** | | T001–T056 | **56** |

| Story | Task count | Priority |
|-------|----------:|----------|
| US1 | 10 | P1 (MVP) |
| US2 | 11 | P1 |
| US3 | 7 | P1 |
| US4 | 8 | P2 |
| Setup/Foundational/Polish | 20 | — |
