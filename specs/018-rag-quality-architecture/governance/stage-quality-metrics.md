# Stage Quality Metrics Catalog (018)

Architecture-level diagnostic metrics from spec §17.

**014 authority**: Feature 014 remains the offline golden/regression authority for **coverage**, **faithfulness**, and **completeness**. Metrics below are diagnostic and offline-alignable. They **do not redefine** 014 golden metric definitions.

| Stage | Metric ID | Purpose |
|-------|-----------|---------|
| Query Understanding | intent_parse_reliability | Successful grounded intent vs clarification/degradation |
| Query Understanding | entity_grounding_honesty | No fabricated entities |
| Planner | intent_fidelity | No re-parse drift vs Understood Query |
| Planner | strategy_alignment | Strategies justified by capabilities + parse signals |
| Engine | retrieval_recall | Relevant candidates under plan constraints (offline-aligned) |
| Engine | filter_effectiveness | Declared filters applied or explicitly residual/unapplied |
| Engine | calibration_honesty | Heterogeneous score provenance retained |
| Evidence | dedup_effectiveness | Redundant collapse without citation attribution loss |
| Evidence | evidence_coverage | complete/partial/missing states accurate |
| Evidence | evidence_quality_signal_completeness | unknown vs populated dimensions |
| Context | token_utilization | Budget used vs available without overflow |
| Context | citation_retention | Included blocks fully mapped through citation chain |
| Context | priority_fidelity | Higher priority classes retained preferentially |
| Answer | grounding_rate | Claims grounded at claim level |
| Answer | unsupported_claim_rate | Ungrounded claims escaping as grounded |
| Answer | citation_correctness | Resolved citations match Context map/chain |
| Answer | conflict_disclosure_rate | Disclosure when conflicts survive |
| Answer | no_answer_correctness | Correct posture under no/weak/missing evidence |

Concrete instrumentation is deferred to a future implementation phase — out of 018 architecture task scope.
