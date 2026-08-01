# Metric Dependency Map (019)

Normative detail: [`../contracts/metric-system.md`](../contracts/metric-system.md).

## Upstream → downstream

```text
Query Understanding quality
        ↓
Planner quality (Plan Fidelity, Strategy Alignment)
        ↓
Retrieval Quality (Recall, Precision, MRR, NDCG)
        ↓
Evidence Quality (sufficiency / coverage diagnostics)
        ↓
Context Quality (citation chain readiness, budget/priority)
        ↓
Faithfulness
        ↓
Groundedness
        ↓
Completeness
        ↓
Citation Accuracy  ←── also depends on Context citation continuity
        ↓
Hallucination Rate

Latency & Cost  ←── cross-cutting over the entire chain
```

## Root-cause annotation rules

1. Score all enabled metrics for the item.
2. Apply Metric Ownership for each failed metric (single primary owner each).
3. Apply dependency order to mark **likely root cause** vs **downstream effect**.
4. Reports MUST show both primary owners and optional root-cause annotation.
5. **Dependency analysis NEVER reassigns Primary Owner.**

## Planner constraint exclusion

Plan filters/constraints that correctly exclude items MUST NOT be scored as Retrieval Engine Recall misses when labels mark them out-of-scope. Wrong constraints are Planner failures (Plan Fidelity / Strategy Alignment).
)
