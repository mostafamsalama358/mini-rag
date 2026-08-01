# Quickstart: RAG Quality Architecture Validation

**Feature**: 018-rag-quality-architecture | **Date**: 2026-07-18

Architecture validation guide. This is **not** an implementation tutorial and does not include coding steps, algorithms, or provider setup.

---

## Prerequisites

- Read [spec.md](./spec.md) §§1–20 and Contracts C1–C12
- Read [plan.md](./plan.md) and [research.md](./research.md)
- Skim [data-model.md](./data-model.md) and `contracts/`
- Optional for offline-gate awareness: Feature 014 answer-quality materials (metrics not redefined here)
- Optional for ownership baseline: `specs/016-architecture-consolidation/governance/ownership-registry.md`

---

## 1. Ownership Mapping Drill (SC-001)

**Goal**: Every quality concern maps to one primary owner.

**Validate**:

1. For each of §§1–20 in the spec, name the primary owning stage/party.
2. Confirm coverage validation and missing-evidence are Evidence-owned (not Answer).
3. Confirm score calibration and candidate lifecycle are Engine-owned.
4. Confirm claim-level verification is Answer-owned as logical sub-responsibilities (not a new owner).
5. Confirm Query Understanding owns Understood Query production; Planner consumes without re-parse.

**Expected**: Complete mapping in under 20 minutes from docs alone.

**Contracts**: [quality-continuity.md](./contracts/quality-continuity.md), [compatibility.md](./contracts/compatibility.md)

---

## 2. Continuity Attribution Drill (SC-002)

**Goal**: Bad-answer vignettes map to the earliest broken contract.

**Validate** (sample vignettes):

| Vignette | Expected earliest contract |
|----------|----------------------------|
| Plan filter ignored in results | C2 (or Planner if never declared) |
| Planner intent conflicts with Understood Query | C9 |
| Definitive answer despite partial/missing evidence | C10 / C7 |
| Conflict present; answer picks one side silently | C4 |
| Citation to non-included document | C5 |
| Claim marked grounded with no support | C12 |
| Unplanned strategy family appears in Engine | C1 |

**Expected**: ≥90% correct attribution on a 12-vignette set in blind review.

---

## 3. Modularity Rejection Drill (SC-003, SC-007)

**Goal**: Parallel paths and mega-stages are rejectable.

**Validate**:

1. Propose “quality-only second retrieval path” → reject via C8 + 016 M0 ([compatibility.md](./contracts/compatibility.md)).
2. Propose merging Planner+Engine+Evidence → reject via C8 / single-responsibility.
3. Propose 014 evaluator as request-path owner → reject via §18 / [quality-observability.md](./contracts/quality-observability.md).
4. Propose Answer as sole coverage authority → reject via C10.

**Expected**: Each rejection cites a contract in under five minutes.

---

## 4. Quality Context & Trace Continuity (SC-008)

**Goal**: Cumulative state and sectioned diagnostics are reviewable.

**Validate**:

1. List Quality Trace sections and producing stages ([quality-observability.md](./contracts/quality-observability.md)).
2. Walk a partial-evidence + budget-pressure narrative:
   - Evidence sets `partial`/`missing`
   - Context records budget omission / priority drops
   - Answer reflects limited/no-answer
   - Quality Context shows degradation history without overwriting upstream ownership
3. Confirm disabled rerank appears in Rerank Trace without inventing rerank results.

**Expected**: Reviewer can name enrichers and append-only rule (C11).

---

## 5. Context Priority & Compression Policy (SC-006)

**Goal**: Stakeholder-readable selection/compression rules without algorithms.

**Validate**:

1. Recite priority order: conflict → primary → supporting → contextual → background → redundant.
2. State compressible vs non-compressible preservation (citation, conflict, grounding).
3. Confirm structural ordering is after priority selection ([evidence-and-context-quality.md](./contracts/evidence-and-context-quality.md)).

**Expected**: Explanation without naming similarity metrics or tokenizers.

---

## 6. Claim-Level Grounding & No-Answer (SC-005, SC-009)

**Goal**: User-visible grounding/no-answer behavior is clear.

**Validate**:

1. Confirm grounded claims require supporting included evidence ([answer-grounding.md](./contracts/answer-grounding.md)).
2. For conditions no/weak/conflicting/partial evidence, ambiguous, out-of-domain, restricted — state expected posture.
3. Confirm empty evidence forbids parametric fill-in.

**Expected**: Stakeholder can describe behaviors without code.

---

## 7. Offline Authority & Feedback Loop (SC-004, SC-010)

**Goal**: Feature 014 remains offline authority.

**Validate**:

1. Confirm 018 does not redefine coverage/faithfulness/completeness golden metrics.
2. Confirm feedback flow: answers → 014 offline → configuration/pack/strategy hints → Composition.
3. Confirm evaluation is not a runtime stage owner.

**Expected**: Checklist pass against [compatibility.md](./contracts/compatibility.md) and [quality-observability.md](./contracts/quality-observability.md).

---

## 8. Compatibility Sweep (014–017)

**Validate**:

| Check | Pass criteria |
|-------|---------------|
| 014 | Offline authority retained |
| 015 | No permanent second answer path; frozen API not redesigned |
| 016 | No owner reassignment; no parallel paths |
| 017 | No ingest job coupling in quality contracts |

---

## Out of Scope for this Quickstart

- Running application servers or writing tests
- Choosing providers, thresholds, or formulas
- Producing `/speckit-tasks` implementation breakdown
- Changing production wiring

---

## Success

All drills above pass → architecture plan artifacts are ready for optional `/speckit-clarify` refinements or a separately authorized `/speckit-tasks` (implementation) phase.
