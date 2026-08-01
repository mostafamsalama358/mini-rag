# Drift Taxonomy Catalog (019)

Normative detail: [`../contracts/observability-monitoring.md`](../contracts/observability-monitoring.md).

| Drift category | Meaning |
|----------------|---------|
| Data Drift | Indexed / corpus content distribution shifts |
| Query Drift | Live query mix shifts vs offline datasets |
| Retrieval Drift | Live retrieval outcome distribution shifts |
| Ranking Drift | Ordering quality proxies shift vs offline IR posture |
| Citation Drift | Citation resolution / mismatch proxies degrade |
| Answer Drift | Answer quality proxies shift |
| Latency Drift | Latency distributions worsen vs baseline window |
| Cost Drift | Cost per request / unit policy worsens vs baseline window |

## Relationship to offline regression

- Offline profile gates remain **primary merge/release quality authority**.
- Drift explains live divergence; may trigger alerts, shadow emphasis, or dataset evolution.
- Persistent drift MUST NOT be “fixed” by silent threshold relaxation.
)
