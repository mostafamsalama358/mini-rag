# Error Taxonomy Catalog (019)

Normative detail: [`../contracts/observability-monitoring.md`](../contracts/observability-monitoring.md).

| Category | Meaning | Typical primary metric owners |
|----------|---------|-------------------------------|
| Retrieval Failure | Relevant material not retrieved or ranking insufficient | Retrieval Engine |
| Planner Failure | Plan/strategy/constraint incorrect vs labels / Understood Query | Retrieval Planner |
| Context Failure | Context assembly / priority / compression / citation-chain readiness | Context Builder (supporting); may surface via Citation Accuracy |
| Citation Failure | Missing, unresolved, or claim-mismatched citations | Answer Generation |
| Grounding Failure | Claims not grounded / not faithful to evidence | Answer Generation |
| Generation Failure | Answer content defects when evidence was sufficient | Answer Generation |
| Evaluation Failure | Evaluation could not score validly | Evaluation system (not a production stage) |
| Infrastructure Failure | Subject outputs/telemetry unavailable | Operational / infra attribution |

**Rules**:

1. Primary category SHOULD align with Metric Ownership for the dominant failed blocking metric.
2. Evaluation Failure and Infrastructure Failure MUST **never** become silent PASS under blocking profiles.
3. Categories do not create new production pipeline stages.
)
