# Quickstart: RAG Evaluation Framework (Architecture Validation)

**Feature**: 019-rag-evaluation-framework | **Date**: 2026-07-18

Architecture-review drills proving the evaluation design — not a coding or CI execution program.

---

## Prerequisites

- Read [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md)
- Skim contracts in [contracts/](./contracts/)
- Related: `specs/014-answer-quality/`, `specs/015-unified-pipeline-migration/`, `specs/016-architecture-consolidation/`, `specs/018-rag-quality-architecture/`

---

## 1. Sole-Path & Non-Ownership Drill (SC-001, SC-011)

**Steps**:

1. List evaluation modes (offline, shadow, monitoring).
2. Confirm none is described as the user-facing answer owner.
3. Confirm Metric Ownership maps to existing 016 concerns; Latency/Cost use ops attribution language only.

**Expected**: No new production RAG stage; M0 freeze respected.

---

## 2. Metric Ownership & Dependency Drill (SC-003, SC-006, SC-013)

**Scenario**: One item fails Recall, Completeness, and Hallucination Rate after relevant chunks were removed upstream.

**Steps**:

1. Assign Primary Owner per failed metric using [contracts/metric-system.md](./contracts/metric-system.md).
2. Apply dependency annotation for likely root cause.
3. Verify Primary Owners were not rewritten by dependency analysis.

**Expected**:

- Recall → Retrieval Engine
- Completeness / Hallucination Rate → Answer Generation (primary), with upstream root-cause annotation allowed
- Exactly one Primary Owner per failed metric

---

## 3. Profile → Gate Mapping Drill (SC-007)

**Steps**:

1. Map Smoke, PR, Nightly, Weekly, Release, Shadow, Production Monitoring to dataset tiers and gate classes ([contracts/evaluation-pipeline.md](./contracts/evaluation-pipeline.md)).
2. Confirm PR requires frozen Core Golden.
3. Confirm no concrete numeric thresholds appear in profile architecture.

**Expected**: Distinct enforcement contexts; PR/Release freeze requirements clear.

---

## 4. Dataset / Benchmark Freeze Drill (SC-008, SC-014)

**Steps**:

1. Walk a Core Golden version through Draft → Frozen.
2. Attempt an in-place label edit on Frozen (should be forbidden; requires new version + changelog/lineage).
3. Compare two Release runs: same frozen benchmark version vs evolved version without bridge.

**Expected**: Reproducibility only with freeze + run metadata + judge version; incomparable evolution is explicit.

---

## 5. Judge Stability Drill (SC-004, SC-005)

**Scenario**: Same item scored conceptually by Rule Judge vs LLM Judge for Faithfulness and Citation Accuracy.

**Steps**:

1. Confirm metric identities unchanged across judge types ([contracts/judge-layer.md](./contracts/judge-layer.md)).
2. Confirm run can record judge version; confidence optional.
3. Confirm mismatched citation still fails Citation Accuracy under either judge *semantics* (implementation not required).

**Expected**: Metrics stable; provenance recordable; no judge-specific parallel metric names.

---

## 6. Experiment Roles Drill (SC-008)

**Steps**:

1. Label two runs Champion vs Challenger on the same frozen benchmark.
2. Produce a BaselineDiff mental model: one injected Recall regression.
3. Confirm Shadow/Canary do not imply a second user-visible answer owner ([contracts/experiment-comparison.md](./contracts/experiment-comparison.md)).

**Expected**: Diff flags only the regression; 015 sole-path preserved.

---

## 7. Drift & Alert vs Offline Authority Drill (SC-009)

**Steps**:

1. Classify a live unsupported-claim spike as Answer Drift.
2. Emit conceptual Drift Alert + Latency Alert.
3. State whether merge authority comes from offline PR Core Gate or from the alert alone.

**Expected**: Alerts notify; offline gates remain primary merge authority by default ([contracts/observability-monitoring.md](./contracts/observability-monitoring.md)).

---

## 8. Lifecycle Loop Drill (SC-012)

**Steps**: Trace Dataset → Evaluation → Reports → Gates → Release → Shadow → Production Monitoring → Dataset Evolution using the lifecycle in [spec.md](./spec.md) / [plan.md](./plan.md).

**Expected**: Closed evaluation ecosystem with no new production stage inserted.

---

## 9. Compatibility Sweep (014–018) (SC-011)

| Check | Pass criteria |
|-------|----------------|
| 014 | Faithfulness/Completeness semantics preserved |
| 015 | Shadow inputs allowed; no second answer owner; SKIP ≠ PASS |
| 016 | No owner reassignment; eval non-production |
| 018 | Diagnostics non-authoritative vs 019 gates; Quality Trace preferred |

Details: [contracts/compatibility.md](./contracts/compatibility.md)

---

## Out of Scope for this Quickstart

- Running pytest, CI jobs, or live pipelines
- Choosing judge models, formulas, or thresholds
- Implementing dashboards or alert routers
- Authoring production golden datasets
- `/speckit-tasks` implementation breakdown

---

## Success

Architecture validation passes when drills 1–9 succeed and reviewers agree the design is ready for optional `/speckit-clarify` follow-ups or a separately authorized `/speckit-tasks` implementation phase.
)
