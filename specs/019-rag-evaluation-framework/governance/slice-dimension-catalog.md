# Slice Dimension Catalog (019)

Normative detail: [`../contracts/observability-monitoring.md`](../contracts/observability-monitoring.md).

Standard slicing dimensions for reports (re-aggregate canonical metrics only):

| Dimension | Purpose |
|-----------|---------|
| domain | Domain Pack / business domain mix |
| language | Query/answer language |
| intent | Understood / labeled intent class |
| query complexity | Complexity band |
| retrieval strategy | Strategies used / expected |
| planner strategy | Planner strategy choices |
| document type | Source document type mix |
| tenant | Tenant / isolation slice |
| context size | Context budget / size band |
| answer length | Answer length band |
| dataset tier | Core / Extended / Adversarial / Benchmark / Online Sample |

Slices do not invent metrics. Blocking gates MAY optionally require no blocker regressions on designated critical slices.
)
