# Contract: Observability, Monitoring, Drift & Alerts

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative information architecture for monitoring, taxonomies, slices, reports, and alerts.

---

## Purpose

Operationalize live quality/ops posture without replacing offline gate authority or inventing a second telemetry model.

---

## Telemetry preference

Prefer Feature **018** Quality Context / Quality Trace fields as enrichment for monitoring and offline alignment. Evaluation Run Metadata remains the evaluation-specific reproducibility record. Do not create a competing parallel telemetry ontology.

---

## Monitoring views (required information architecture)

Quality Health · Retrieval Health · Planner Health · Ops Health · Gate Status · Defect Hotspots · Drift Board · Experiment Board

Concrete BI/observability products are out of scope.

---

## Error Taxonomy

Retrieval Failure · Planner Failure · Context Failure · Citation Failure · Grounding Failure · Generation Failure · Evaluation Failure · Infrastructure Failure

**Rules**:

1. Item failures SHOULD carry a primary category aligned with dominant failed blocking metric ownership
2. Evaluation Failure / Infrastructure Failure MUST NOT become silent PASS under blocking profiles
3. Categories standardize reporting; they do not create new production stages

---

## Drift Taxonomy

Data Drift · Query Drift · Retrieval Drift · Ranking Drift · Citation Drift · Answer Drift · Latency Drift · Cost Drift

**Relationship to offline regression**:

- Offline gates remain primary merge/release quality authority
- Drift explains live divergence and may trigger alerts / shadow emphasis / dataset evolution
- Persistent drift MUST NOT be “fixed” by silent threshold relaxation

---

## Alert Architecture

| Category | Role vs gates |
|----------|---------------|
| Threshold Alert | May mirror Ops/Drift inputs |
| Regression Alert | Often accompanies gate FAIL |
| Trend Alert | Usually advisory early warning |
| Drift Alert | Companion to Online Drift Gate |
| Cost Alert | Companion to Ops Gate |
| Latency Alert | Companion to Ops Gate |

**Rule**: Alerts notify; gates decide. An alert alone is not merge PASS.

---

## Slice Architecture

Standard dimensions: domain · language · intent · query complexity · retrieval strategy · planner strategy · document type · tenant · context size · answer length · dataset tier

Slices re-aggregate canonical metrics; they do not invent metrics.

---

## Report types

Item · Run · Trend · Slice · Executive summary

Executive views MAY use composite scores with drill-down to owners, metrics, and taxonomies.

---

## Acceptance

Contract review fails if:

- Monitoring invents a second full telemetry model instead of preferring 018 traces where available
- Drift is treated as automatic merge authority over offline Core gates by default
- Alerts are defined as sufficient for release PASS without gates
- Error/Drift taxonomies are omitted or collapsed into a single opaque “quality” flag
)
