# Quickstart: Pharmacy Recommendation Capability (Architecture Validation)

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22

Architecture-review drills proving the recommend-mode design — not a coding sprint. Implementation execution belongs to `/speckit-tasks` and later implement.

---

## Prerequisites

- Read [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md)
- Skim [contracts/](./contracts/)
- Read [ADR-020-001](./governance/adr-020-001-recommendation-as-capability.md)
- Related: `specs/015-…`, `specs/016-…`, `specs/018-…`, `specs/019-…`

---

## 1. Sole-Path & ADR Drill (SC-007)

**Steps**:

1. Confirm ADR-020-001 rejects Recommendation Service, Recommendation API, parallel path, new sole owner.
2. Walk [ownership-and-flow](./contracts/ownership-and-flow.md) and map each logical step to an existing 016 concern.
3. Confirm no new production orchestrator is mandated.

**Expected**: Capability-only; M0 freeze respected.

---

## 2. Frozen `/answer` Contract Drill (FR-011)

**Steps**:

1. Diff recommend-mode against [compatibility](./contracts/compatibility.md) and 015 api-stability.
2. Confirm clarification uses existing `needs_clarification` / signals.
3. Confirm Trace is not a new mandatory public field.

**Expected**: No wire break; content-only recommend.

---

## 3. Need Frame & Taxonomy Drill (US1, US3)

**Scenario**: “دواء للحموضة؟” vs “مشكلة في البطن” (ambiguous).

**Steps**:

1. Populate optional NeedFrame fields only as present.
2. Map through Symptom Taxonomy (many-to-many / hierarchy).
3. Assert ambiguity → clarification path per policy.

**Expected**: High-confidence acidity maps to indication tags; ambiguous need clarifies—not a dump of unrelated classes.

---

## 4. Ranking Signals Drill (FR-006)

**Steps**:

1. List named signals from [ranking-and-policy](./contracts/ranking-and-policy.md).
2. Confirm no fixed weights appear in plan/contracts.
3. Confirm operator Trace can show rank contribution without end-user score dump.

**Expected**: Reviewable & explainable ranking; Policy-owned weights.

---

## 5. Safety Subset Drill (US2, SC-002)

**Scenario**: Painkiller need + pregnancy population.

**Steps**:

1. Apply Safety Filtering for pregnancy dimension.
2. Confirm unknown ≠ safe.
3. Confirm catalog lists future dimensions without requiring v1 implementation.

**Expected**: Avoid/contraindicated not silently first-line; extensible model intact.

---

## 6. Product Identity Drill (SC-010)

**Scenario**: Multiple Panadol lines/SKUs in corpus.

**Steps**:

1. Apply Brand → Line → Strength → Package rules.
2. Prefer need-specific line when tags differ.
3. Ensure package-only variants do not fill multiple slots when irrelevant.

**Expected**: No false duplicates / false merges.

---

## 7. Explanation Policy Drill (US4, FR-008)

**Steps**:

1. Draft a sample recommend answer using evidence-only rationale.
2. Reject any sentence that cites hidden scores or unsupported superiority.
3. Confirm citations present for retrieval-backed claims.

**Expected**: Recommendation ≠ medical advice; grounded language.

---

## 8. Evaluation Bridge Drill (SC-008, US5)

**Steps**:

1. Map spec metrics to [evaluation-bridge](./contracts/evaluation-bridge.md).
2. Confirm 019 owns implementation; 020 does not add request-path eval.
3. Sketch one RecommendEvalCase (allow/forbid, safety expectation, clarification flag).

**Expected**: Clear 020↔019 separation; profile-shaped coverage.

---

## 9. Trace / Explainability Drill (US6, SC-009)

**Steps**:

1. For one retained and one excluded candidate, list Matched Indications, Evidence, Safety Outcome, Rank Contribution.
2. Confirm end-user answer does not require those internals.

**Expected**: Operator-complete; user-safe.

---

## Sign-off

| Drill | Pass? |
|-------|-------|
| 1 Sole-path / ADR | ☐ |
| 2 Frozen contract | ☐ |
| 3 Need/Taxonomy | ☐ |
| 4 Ranking signals | ☐ |
| 5 Safety subset | ☐ |
| 6 Product identity | ☐ |
| 7 Explanation policy | ☐ |
| 8 Evaluation bridge | ☐ |
| 9 Trace explainability | ☐ |

When all pass, feature design is ready for `/speckit-tasks`.
