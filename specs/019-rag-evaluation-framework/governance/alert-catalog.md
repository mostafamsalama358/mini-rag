# Alert Catalog (019)

Normative detail: [`../contracts/observability-monitoring.md`](../contracts/observability-monitoring.md).

| Alert category | Meaning | Relation to gates |
|----------------|---------|-------------------|
| Threshold Alert | Monitored signal crossed a policy threshold | May mirror Ops/Drift inputs |
| Regression Alert | Offline/scheduled run regressed vs baseline/champion | Often accompanies gate FAIL |
| Trend Alert | Multi-window adverse trend without single-point breach | Usually advisory |
| Drift Alert | One or more Drift Taxonomy categories elevated | Online Drift Gate companion |
| Cost Alert | Cost posture breach or sharp increase | Ops Gate companion |
| Latency Alert | Latency posture breach or sharp increase | Ops Gate companion |

## Binding rule

**Alerts notify; gates decide.** An alert alone is not merge PASS.
)
