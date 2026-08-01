# Contract: Ownership and Logical Flow

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22  
**Authority**: [ADR-020-001](../governance/adr-020-001-recommendation-as-capability.md), Features 016 / 009 / 010 / 004 / 013

---

## Ownership (normative)

| Concern | Sole owner / concern | Forbidden |
|---------|----------------------|-----------|
| Recommend intent + NeedFrame | Query Understanding | New intent microservice |
| Symptom Taxonomy + IndicationTag vocab + RecommendationPolicy YAML | Domain Pack (pharmacy) | Hard-coded one-off dicts as sole SoT without pack versioning |
| Constraints, hybrid retrieval, fusion, rerank, ranking signal inputs | Retrieval (planner/engine as applicable) | Parallel recommend retriever owner |
| Safety Filtering + Product Identity application | Pack policy applied on sole path | New Safety Service owner |
| Recommendation Score composition | Policy-governed behavior on sole path | New Ranking Service owner |
| Answer text + Explanation Policy | Answer Generation | Second answer composer path |
| Metric runners / gates | Feature 019 | Request-path evaluation owner |

**M0**: No parallel production recommend path. Logical flow ≠ new pipeline.

---

## Logical flow (normative concern order)

```text
Need
  → Need Normalization
  → Symptom Taxonomy Mapping
  → Candidate Constraints
  → Metadata Filtering
  → Hybrid Retrieval
  → Fusion
  → Reranking
  → Safety Filtering
  → Recommendation Ranking
  → Answer Generation
```

### Clarifications

1. Steps MAY be thin or skipped when signals absent (e.g. no formulary preference).
2. Steps MUST map onto existing stage libraries/orchestrator responsibilities.
3. Documenting this order MUST NOT be interpreted as license to create `RecommendationPipeline` as a second production orchestrator.
4. Recommendation Ranking consumes candidates already produced by retrieval + safety; it does not replace hybrid retrieval.

---

## Acceptance

- Architecture tests/docs can point each step to an existing owner.
- No module is designated `active_production_owner` for “Recommendation” in 016 registries without exception ADR.
