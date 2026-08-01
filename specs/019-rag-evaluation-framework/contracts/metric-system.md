# Contract: Metric System

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative rules for canonical metrics, ownership, dependencies, honesty, confidence, and composites.

---

## Purpose

Ensure every scored quality/ops signal is stable, attributable, and gate-ready without formulas or thresholds.

---

## Canonical metrics

Recall · Precision · MRR · NDCG · Plan Fidelity · Strategy Alignment · Faithfulness · Groundedness · Completeness · Citation Accuracy · Hallucination Rate · Latency · Cost

Faithfulness and Completeness MUST remain semantically compatible with Feature 014. Groundedness MUST remain compatible with Feature 018 claim-level continuity intent.

---

## Ownership (normative)

| Metric | Primary Owner | Supporting Stages | Default posture |
|--------|---------------|-------------------|-----------------|
| Recall | Retrieval Engine | Planner, Evidence | Blocking when labeled |
| Precision | Retrieval Engine | Planner | Blocking when labeled |
| MRR | Retrieval Engine | Planner | Blocking in retrieval/Release profiles when labeled; else Diagnostic |
| NDCG | Retrieval Engine | Planner | Blocking in retrieval/Release profiles when labeled; else Diagnostic |
| Plan Fidelity | Retrieval Planner | Query Understanding | Blocking when labeled |
| Strategy Alignment | Retrieval Planner | Query Understanding | Blocking when labeled; else Diagnostic |
| Faithfulness | Answer Generation | Evidence, Context | Blocking |
| Groundedness | Answer Generation | Evidence, Context | Blocking |
| Completeness | Answer Generation | Evidence, Retrieval Engine | Blocking when facets labeled |
| Citation Accuracy | Answer Generation | Context Builder, Evidence | Blocking |
| Hallucination Rate | Answer Generation | Evidence, Context | Blocking |
| Latency | Whole Pipeline (ops attribution) | All stages | Blocking in Ops/Release/Monitoring; Diagnostic in Smoke |
| Cost | Whole Pipeline (ops attribution) | All stages | Blocking in Ops/Release/Monitoring; Diagnostic in Smoke |

**Rules**:

1. Exactly one Primary Owner per failed metric
2. Supporting Stages MUST NOT split primary ownership
3. Whole Pipeline ops attribution is an evaluation concept — not a new 016 production owner
4. Profiles may move Diagnostic↔Blocking posture; they MUST NOT redefine metric identity

---

## Dependency model

Architectural order (upstream → downstream):

Query Understanding → Planner quality → Retrieval Quality → Evidence Quality → Context Quality → Faithfulness → Groundedness → Completeness → Citation Accuracy → Hallucination Rate

Latency & Cost are cross-cutting.

**Rules**:

1. Upstream failures MAY cause downstream metric failures
2. Root-cause annotation MAY nominate an upstream stage
3. Root-cause annotation MUST NOT rewrite Primary Owner for each failed metric
4. Reports MUST expose both ownership and optional root-cause annotation

---

## Honesty rules

- Missing required labels ⇒ metric status **N/A** (not zero)
- Correct labeled no-answer ⇒ not automatic hallucination failure
- Absent citation map with assertive grounded answer ⇒ fail groundedness/citation or dedicated ungrounded-generation failure — never silent pass
- Planner-correct exclusions MUST NOT be scored as Engine Recall misses when labels mark out-of-scope

---

## Metric confidence (optional fields)

confidence · judge_version · agreement · evaluation_provenance

Absence is valid; missing confidence ≠ failure.

---

## Composite quality scores

Overall Quality · Retrieval Quality · Planning Quality · Generation Quality · Production Health

**Rules**:

1. Composites are derived views with mandatory drill-down
2. Partial constituents ⇒ partial composite + explicit coverage declaration
3. Composites do not replace per-metric gates unless a profile explicitly says otherwise (default: advisory)

---

## Acceptance

Contract review fails if:

- Any canonical metric lacks a single Primary Owner
- A design redefines Faithfulness/Completeness incompatibly with 014
- Composites are the only blocking signal without per-metric drill-down
- Dependency analysis reassigns Primary Owner silently
)
