# Ownership Map — Pharmacy Recommendation (020)

| Concern | Owner (016) | 020 artifact / code |
|---------|-------------|---------------------|
| Recommend intent + NeedFrame | Query Understanding | `src/core/query_parser/` |
| Symptom Taxonomy / indication tags / policy YAML | Domain Pack | `src/fields/pharmacy/*.yaml`, `recommend_pack.py` |
| Constraints, hybrid, fusion, rerank, ranking signals | Retrieval | `src/services/rag/recommend/`, adapters, orchestrator hook |
| Safety filter + identity | Pack policy on sole path | `safety.py`, `identity.py` |
| Answer + Explanation Policy | Answer Generation | `answer_generation.yaml`, `recommend_explanation_policy.py` |
| Recommendation Trace | Diagnostics / Quality Context | `trace.py`, `diagnostics.log_recommend_decision` |
| Metric runners / gates | Feature 019 | `evaluation-bridge.md`, profile index bridge |

**Not an owner:** `src/services/rag/recommend/` (internal helpers only). See ADR-020-001.
