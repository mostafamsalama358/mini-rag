# Retrieval Evaluation Notes (019)

IR metrics (Recall, Precision, MRR, NDCG) are evaluable **independent of answer generation**.

| Topic | Rule |
|-------|------|
| Primary Owner | Retrieval Engine ([`metric-ownership-registry.md`](./metric-ownership-registry.md)) |
| Scope | Offline primary; online proxy optional |
| Cutoffs | Declared in run policy and recorded on results |
| Planner exclusions | Correct constraint exclusions are not Engine Recall misses ([`metric-dependency-map.md`](./metric-dependency-map.md)) |
| Labels | Missing relevance labels ⇒ N/A, not zero |

See also Feature 018 retrieval quality diagnostics (non-authoritative vs 019 gates).
)
