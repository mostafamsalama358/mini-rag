# Contract: Experiment Comparison

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative comparison roles and diff semantics — no deployment mechanics.

---

## Purpose

Make Baseline/Champion/Challenger (and related) evaluation posture explicit and comparable.

---

## Roles

| Role | Meaning |
|------|---------|
| Baseline | Reference for deltas |
| Candidate | Proposed change under evaluation |
| Champion | Accepted production-quality reference for a release line |
| Challenger | Contender seeking to replace champion via gates + review |
| Shadow | Non-user-visible evaluation on live-like inputs |
| Canary | Limited-exposure observation role for evaluation comparison |

Traffic shifting, percentages, routers, and infra orchestration are **out of scope**.

---

## Normative rules

1. Comparisons MUST pin compatible frozen dataset/benchmark versions, or explicitly declare a controlled evolution bridge.
2. Champion replacement is a governance/evaluation outcome, not an automatic single-metric win.
3. Shadow/Canary evaluation MUST remain compatible with Feature 015 sole user-visible path rules.
4. Experiment role is recorded on Evaluation Run Metadata.
5. BaselineDiff MUST list metric deltas, optional composite deltas, and regressed item ids — and MUST NOT false-flag unchanged items.
6. Dual-run / shadow sides may both be scored for reports; user-visible ownership stays singular (016/015).

---

## Acceptance

Contract review fails if:

- Canary/Shadow roles imply a second production answer owner
- Champion replacement has no gate/review concept
- Diffs omit dataset/benchmark version compatibility checks
)
