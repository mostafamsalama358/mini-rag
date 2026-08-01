# Composite Score Catalog (019)

Derived reporting indicators — **no formulas** defined here.

| Composite score | Architectural purpose |
|-----------------|----------------------|
| Overall Quality Score | Executive multi-metric posture for a run/window |
| Retrieval Quality Score | Rollup of Recall/Precision/MRR/NDCG as available |
| Planning Quality Score | Rollup of Plan Fidelity / Strategy Alignment |
| Generation Quality Score | Rollup of Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate |
| Production Health Score | Live quality proxies + Latency + Cost posture |

## Rules

1. Composites are derived views with mandatory drill-down to metrics, owners, and error taxonomy.
2. Partial constituents ⇒ partial composite + explicit coverage declaration.
3. Default: advisory — do not replace per-metric blocking gates unless a profile explicitly names otherwise.
)
