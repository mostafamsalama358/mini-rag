# Quickstart: Production Scalability & Reliability Validation

**Feature**: `017-scalability-reliability` | **Date**: 2026-07-18  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Validation/run guide for production confidence. Not an implementation tutorial.

---

## Prerequisites

- Docker Compose stack healthy (API + workers + PostgreSQL + broker) per project docs
- Feature config version validated (see FR-049); scalable-path enablement controllable per project cohort
- Golden corpus fixtures available under the project’s ingest test fixture paths (extend with large/corrupt/degraded cases as listed below)
- Operator access to job status/history via correlation identity

---

## Contracts under test

| Contract | Path |
| -------- | ---- |
| Lifecycle | [contracts/job-lifecycle.md](./contracts/job-lifecycle.md) |
| Publishing | [contracts/publishing-semantics.md](./contracts/publishing-semantics.md) |
| Stages | [contracts/stage-contracts.md](./contracts/stage-contracts.md) |
| Admission / capacity | [contracts/admission-capacity.md](./contracts/admission-capacity.md) |
| Modes / health | [contracts/operational-modes.md](./contracts/operational-modes.md) |
| Observability | [contracts/observability-audit.md](./contracts/observability-audit.md) |
| Data model | [data-model.md](./data-model.md) |

---

## Baseline (R0)

1. Enable instrumentation (lifecycle, progress, admission, health, mode signals).
2. Ingest a small normal document; record `correlation_id`.
3. **Expect**: Full stage history reconstructible; terminal `Completed` or explicit failure; capacity claim released.

---

## Scenario A — Happy path + degraded/fail matrix

| Fixture | Expect |
| ------- | ------ |
| Clean supported doc | `Completed`; parse `success`; fully committed Active Version |
| Partially recoverable | `Completed With Warnings` or `Failed` if min-content gate fails; never empty success |
| Unreadable/corrupt | `Failed`; ownership `document_quality`; no Active Version change |

---

## Scenario B — Large document + resume

1. Submit large-document profile job under concurrent small-doc load.
2. **Expect**: Small docs continue (service protection / fairness); large job progress visible; memory within budget.
3. Restart a worker mid-job.
4. **Expect**: Resume-eligible continues from checkpoint or explicit terminal failure; no duplicate Active Version; orphans reclaimed (SC-013/SC-019).

---

## Scenario C — Atomic + exactly-once publish

1. Document with Active Version V1; submit replacement V2.
2. Search during Enrichment/Indexing/Publishing → observe V1 only.
3. After `Completed` / `Completed With Warnings` → observe V2 only.
4. Force retry/duplicate completion after success → no second publish (SC-011/SC-018).

---

## Scenario D — Cancel / timeout / reclaim

1. Cancel mid-flight; optionally run timeout fixture.
2. **Expect**: Terminal `Cancelled` / `Timed Out`; previous Active Version unchanged; capacity released; no partial searchable V2 (SC-012).

---

## Scenario E — Overload & back-pressure

1. Burst submissions beyond capacity.
2. **Expect**: Explicit delay/reject ≥ 99% of excess within interactive budget (SC-002); no unbounded accept.
3. Slow downstream stage → upstream regulates (stage flow control).

---

## Scenario F — Dependency unavailable / circuit

1. Force a required dependency Unavailable.
2. **Expect**: Dependent work fails fast or defers; unrelated classes continue; no cascade (SC-015).
3. Restore health → Normal processing resumes.

---

## Scenario G — Poison / dead-letter

1. Repeat permanent failure for same version past policy.
2. **Expect**: Quarantine/poison; automatic capacity consumption stops; operator can inspect and disposition.

---

## Scenario H — Operational modes

Exercise Maintenance, Recovery, Admission Restricted briefly.

**Expect**: Admission/processing matches [operational-modes.md](./contracts/operational-modes.md); mode effects visible in history.

---

## Scenario I — Rollout governance drill

1. Enable canary cohort (R2).
2. Pass promotion gates (or inject rollback-criterion defect).
3. **Expect**: Expand only with evidence; rollback within SC-008 time band (SC-024).

---

## Suggested automated suites (implementation phase)

```text
pytest tests/unit/.../ingest_reliability/ -q
pytest tests/integration/ingestion/ -q
pytest tests/contract/ -q -k "ingest or publish or lifecycle"
```

Record pass/fail and key metrics in `specs/017-scalability-reliability/quickstart-results.json` when runs are executed.

---

## Exit criteria for “quickstart green”

- [ ] Scenarios A–D pass on golden + large fixtures
- [ ] Scenario E demonstrates explicit back-pressure
- [ ] Scenario F contains dependency failure without collapse
- [ ] Correlation-id history reconstruction works (SC-023 sample)
- [ ] No partial publish / dual Active Version observed
- [ ] Capacity claims return to released after terminal paths
