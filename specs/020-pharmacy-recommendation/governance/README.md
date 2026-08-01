# Pharmacy Recommendation Capability — Governance

**Feature**: 020-pharmacy-recommendation  
**ADR**: [adr-020-001-recommendation-as-capability.md](./adr-020-001-recommendation-as-capability.md)

## Scope

Recommendation is a **Domain Pack capability** on the sole Answer + Retrieval path.

**Forbidden**
- Recommendation Service (microservice / new sole owner)
- Recommendation API (dedicated production HTTP resource)
- Parallel production recommend pipeline
- Breaking frozen `/answer` field names (015)

## Artifacts

| File | Purpose |
|------|---------|
| adr-020-001-… | Binding architecture decision |
| ownership-map.md | Concern → existing owner |
| recommend-metric-catalog.md | Metrics (019 implements runners) |
| eval-runbook.md | Offline eval bridge |
| defect-attribution.md | Failure buckets |
| operator-trace-guide.md | How to read RecommendationTrace |

Internal code helpers under `src/services/rag/recommend/` are **not** a 016 production owner.
