# Metric Ownership Registry (019)

Normative detail: [`../contracts/metric-system.md`](../contracts/metric-system.md).

**Rule**: Exactly one Primary Owner per failed metric. Supporting Stages are diagnostic only.

| Metric | Primary Owner | Supporting Stages | Blocking vs Diagnostic | Evaluation Scope | Contract Ref |
|--------|---------------|-------------------|------------------------|------------------|--------------|
| Recall | Retrieval Engine | Retrieval Planner, Evidence | Blocking when labeled | Offline; online proxy optional | metric-system |
| Precision | Retrieval Engine | Retrieval Planner | Blocking when labeled | Offline; online proxy optional | metric-system |
| MRR | Retrieval Engine | Retrieval Planner | Blocking in retrieval/Release when labeled; else Diagnostic | Offline; online proxy optional | metric-system |
| NDCG | Retrieval Engine | Retrieval Planner | Blocking in retrieval/Release when labeled; else Diagnostic | Offline; online proxy optional | metric-system |
| Plan Fidelity | Retrieval Planner | Query Understanding | Blocking when labeled | Offline; online diagnostic optional | metric-system |
| Strategy Alignment | Retrieval Planner | Query Understanding | Blocking when labeled; else Diagnostic | Offline; online diagnostic optional | metric-system |
| Faithfulness | Answer Generation | Evidence, Context | Blocking | Offline primary; online proxy / shadow | metric-system |
| Groundedness | Answer Generation | Evidence, Context | Blocking | Offline primary; online proxy / shadow | metric-system |
| Completeness | Answer Generation | Evidence, Retrieval Engine | Blocking when facets labeled | Offline primary; online proxy optional | metric-system |
| Citation Accuracy | Answer Generation | Context Builder, Evidence | Blocking | Offline primary; online proxy / shadow | metric-system |
| Hallucination Rate | Answer Generation | Evidence, Context | Blocking | Offline primary; online proxy / monitoring | metric-system |
| Latency | Whole Pipeline (ops attribution) | All production stages | Blocking in Ops/Release/Monitoring; Diagnostic in Smoke | Offline + online + monitoring | metric-system |
| Cost | Whole Pipeline (ops attribution) | All production stages | Blocking in Ops/Release/Monitoring; Diagnostic in Smoke | Offline + online + monitoring | metric-system |

**Notes**:

- Whole Pipeline (ops attribution) is an **evaluation attribution sink** — not a new 016 production sole owner.
- Faithfulness / Completeness remain semantically continuous with Feature 014.
)
