# Contract: Quality Observability (Context, Trace, Metrics, Feedback)

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative contracts for Quality Context, Quality Trace, stage metrics, offline feedback, and extension points.

---

## Purpose

Enable defect attribution, offline evaluation, and configuration improvement without changing runtime ownership.

---

## A. Quality Context

Cumulative accompanying metadata. Does **not** replace Understood Query, Plan, Retrieval Result, Evidence Pack, Context, or Answer Result.

### Example fields

Ambiguity, retrieval confidence, coverage/sufficiency, evidence confidence, conflict summary, citation completeness, budget usage, grounding status, degradation history.

### Rules

1. Every stage MAY enrich.
2. Enrichments are additive or namespaced to the enriching stage.
3. No stage may overwrite upstream ownership fields (C11).
4. Downstream stages use Quality Context only for decisions they already own.

---

## B. Quality Trace

Append-only sectioned diagnostics for observability and Feature 014 offline analysis.

| Section | Producer |
|---------|----------|
| Plan Trace | Planner |
| Retrieval Trace | Engine |
| Expansion Trace | Engine |
| Fusion Trace | Engine |
| Rerank Trace | Engine |
| Evidence Trace | Evidence |
| Context Trace | Context |
| Generation Trace | Answer |
| Verification Trace | Answer (logical verification) |

### Rules

1. Stages append; they do not erase upstream sections.
2. Degradation, residual filters, sufficiency, budget omissions, and grounding outcomes SHOULD appear in the relevant section.
3. Full external API exposure of Trace is not required (015 freeze).

---

## C. Stage Quality Metrics

Architecture-level metrics per [spec.md](../spec.md) §17 (Planner alignment, Engine recall/filter effectiveness, Evidence dedup/coverage, Context token/citation retention, Answer grounding/unsupported-claim/citation correctness, etc.).

### Rules

1. Metrics are diagnostic and offline-alignable.
2. They MUST NOT redefine Feature 014 golden metrics (coverage, faithfulness, completeness).
3. Concrete instrumentation is deferred to implementation planning.

---

## D. Offline Feedback Loop (Feature 014)

```text
Answers (prod/shadow)
  → Offline Evaluation (014)
  → Configuration / pack / strategy-hint feedback
  → Composition wires runtime
```

### Rules

1. Evaluation remains offline; never a request-path owner.
2. Feedback may tighten configuration and extension profiles.
3. Feedback MUST NOT create parallel retrieval/answer paths.
4. On disagreement with stage heuristics, **014 wins** for release/cutover authority.

---

## E. Extension Points

Per-stage extension surfaces (Query Understanding, Planner, Engine, Evidence, Context, Answer Generation) as in [spec.md](../spec.md) §19.

### Rules

1. Composition remains sole wiring authority.
2. Extensions MUST preserve C1–C12 and sole-owner boundaries.
3. Extensions MAY tighten quality; MUST NOT weaken C2/C5/C7/C8/C9/C10/C12.

---

## Acceptance

Designs that make 014 a runtime owner, overwrite upstream Quality Context, or omit Trace sections required for attribution fail review.

---

## Non-Goals

- Choosing log backends or metric systems
- Defining storage schema for traces
- Sprint tasks for instrumentation
