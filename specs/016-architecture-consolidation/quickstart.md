# Quickstart: Architecture Consolidation Validation

**Feature**: 016-architecture-consolidation | **Date**: 2026-07-18

Validation/run guide for governance gates. This is **not** an implementation tutorial and does not include coding steps.

---

## Prerequisites

- Read [spec.md](./spec.md) Principles, Invariants, Anti-Patterns, Governance
- Read [plan.md](./plan.md) and [research.md](./research.md)
- Have access to architecture docs / agent context that claim production dependencies
- For runtime gates (M1+): working environment capable of running existing answer quality / golden checks (mechanism owned by Offline Evaluation / 015 — not redesigned here)

---

## 1. Architecture Validation — Capability Cards

**Goal**: Every in-scope capability is specified without requiring code inspection for ownership rules.

**Validate**:

1. For Answer, Ingest, Search, Offline Evaluation, confirm Purpose / Required Concerns / Required Contracts / Ownership / Allowed / Forbidden Dependencies exist in the spec.
2. Confirm no capability identity depends on a single mandatory global stage sequence (P14).
3. Confirm every Architecture Decision maps to an ADR or Principle/Invariant ([data-model.md](./data-model.md) ArchitectureDecision).

**Expected**: Reviewer can answer ownership questions from docs alone (SC-001).

---

## 2. Architecture Validation — Anti-Patterns & Governance

**Goal**: Drift proposals are rejectable.

**Validate**:

1. Pick a hypothetical “second production retrieval path.”
2. Reject it by citing [contracts/governance.md](./contracts/governance.md) + Forbidden Patterns (AP1/AP10).
3. Confirm exception path requires ADR with scope/duration/exit.

**Expected**: Rejection in under five minutes (SC-012).

---

## 3. Lifecycle Honesty Check

**Goal**: Inactive capabilities are not documented as production-complete.

**Validate**:

1. List capabilities/concerns marked Activation Pending / Dormant / Research (at minimum: structured knowledge per ADR-004).
2. Grep/review agent and architecture docs for claims that those are production stages or completed production dependencies.
3. Confirm lifecycle vocabulary matches [contracts/lifecycle.md](./contracts/lifecycle.md).

**Expected**: Zero false production-complete claims (SC-011).

---

## 4. Dependency Boundary Review

**Goal**: Layer rules hold as architecture policy.

**Validate**:

1. Walk [contracts/dependency-boundaries.md](./contracts/dependency-boundaries.md) matrix.
2. Confirm Composition exclusivity for wiring/selection.
3. Flag any known core→concrete infrastructure dependencies as M5 debt (not a pass until M5).

**Expected**: Documented compliance target; no “accepted forever” inward violations without ADR.

---

## 5. Owner Selection Dry-Run

**Goal**: Contested concern uses criteria, not history.

**Validate**:

1. Choose one historically contested concern (e.g. retrieval execution or chunking).
2. Score candidates with Owner Selection Criteria.
3. Explicitly reject age/folder/history as tie-breakers.
4. Record whether an ADR is required (only if alternatives were genuinely valid).

**Expected**: Written selection rationale suitable for OwnershipBinding.selection_rationale.

---

## 6. Migration Phase Gate Smoke (Process)

**Goal**: Phases are outcome-gated.

**Validate** for each phase M0–M8 in plan:

1. Outcome is observable.
2. Exit gate category is named (Architecture/Code/Runtime/Operational).
3. Retirement phases require prior sole-owner phases (P11).

**Expected**: No phase allows Retire After Cutover before sole owner.

---

## 7. Runtime Gate — Answer Sole Owner (M1)

**Goal**: User-visible Answer path is singular; quality within tolerance.

**Setup**: Use the existing answer cutover vehicle (015) to place production in sole-path mode when ready.

**Validate**:

1. Production configuration/wiring exposes one user-visible Answer owner (not dual user-visible).
2. Transitional diagnostics, if present, are not the response owner.
3. Run the existing offline/golden quality gate; compare to pre-cutover baseline within agreed tolerance.
4. External answer contract unchanged ([contracts/api-stability.md](./contracts/api-stability.md)).

**Expected**: SC-006, SC-010; ADR-003 holds.

---

## 8. Runtime Gate — Ingest/Chunking Sole Path (M4)

**Goal**: One chunking ownership model for production ingest.

**Validate**:

1. No alternate production chunking entrypoint remains selectable.
2. Critical formats still produce retrievable content.
3. If embed-text policy changed materially: re-index completed or waiver recorded (research R-010).

**Expected**: SC-007; compatibility event handled.

---

## 9. Operational — Rollback Drill (pre-M7)

**Goal**: Rollback exists before retirement wave.

**Validate**:

1. Document restore of prior path selection / prior release.
2. Execute drill in non-production or approved window.
3. Confirm retirement does not proceed without drill evidence.

**Expected**: V-O3 satisfied before M7.

---

## 10. Process — Scope Guard

**Goal**: Consolidation review did not absorb Out of Scope work.

**Validate**: Checklist that acceptance did **not** require:

- Perf optimization program
- Algorithm redesign
- API redesign
- DB redesign
- Implementation task list inside 016 artifacts

**Expected**: V-P2 pass.

---

## Related Artifacts

| Artifact | Role |
|----------|------|
| [spec.md](./spec.md) | Normative architecture |
| [plan.md](./plan.md) | Planning summary |
| [research.md](./research.md) | Decision rationale |
| [data-model.md](./data-model.md) | Governance entities |
| [contracts/](./contracts/) | Enforceable contracts |
| `specs/015-unified-pipeline-migration/` | Answer cutover vehicle (assumed) |

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Cannot determine owner from docs | Inventory/docs drift or missing OwnershipBinding | Fix docs; do not invent package winner in 016 |
| Dual responses in production | Diagnostic path acting as owner | Violates I10; fix Composition selection |
| Quality cliff at M1 | Owner immature vs criteria | Revisit Owner Selection; do not retire prior path |
| “Knowledge incomplete” blocking consolidation | Treating pending capability as required stage | Apply ADR-004 lifecycle |
| Review demands coding plan | Scope creep | Point to Out of Scope + FR-001 |
