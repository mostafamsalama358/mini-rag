# Operator Trace Guide — RecommendationTrace

## Where to look

- Structured logs: `RECOMMEND DECISION` via `services.rag.diagnostics.log_recommend_decision`
- In-memory: `UnifiedPipelineResult.recommend_trace` / `recommend_decision` (internal — **not** frozen `/answer` fields)

## Per candidate

| Field | Meaning |
|-------|---------|
| matched_indications | Taxonomy/tag hits |
| evidence_pointers | Evidence refs |
| safety_outcome | pass / demote / exclude / unknown |
| rank_contribution / signal_breakdown | Ranking signal contributions |

## End-user boundary

Do not dump hidden weights into the user-facing `answer` string. Use Explanation Policy qualitative rationale + citations only.
