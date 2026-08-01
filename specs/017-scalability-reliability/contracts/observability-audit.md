# Contract: Observability & Auditability

**Feature**: 017-scalability-reliability | **Version**: 1.0.0  
**Normative for**: Application (Ingest) + operators

---

## Purpose

Ensure every job is diagnosable end-to-end without log archaeology, and that operational signals cover lifecycle, capacity, health, and recovery.

---

## Correlation identity

- Every job has a `correlation_id` from admission through terminal outcome.
- All stage events, validations, retries, cancellations, orphan recoveries, and mode effects that affect the job MUST carry this identity.
- Operators MUST be able to reconstruct the full admission→terminal path from history keyed by correlation identity (FR-058 / SC-023).

---

## Required signal classes

| Class | Examples |
| ----- | -------- |
| Lifecycle | State transitions with timestamps and cause |
| Progress | progressing / waiting / stalled; stage; coarse progress |
| Validation | Gate name, pass/fail, reason |
| Retry | Attempt, eligibility, outcome |
| Failure | Class, ownership, reason, stage |
| Capacity | Accept / delay / reject; back-pressure; claim held/released |
| Health / mode | Component health; operational mode |
| Publish | Publish Completion; Active Version switch; exactly-once no-op |
| Orphan | Detection, ownership, recovery outcome |
| Poison / dead-letter | Quarantine and disposition |

---

## Operational history completeness

Each job retains:

- lifecycle history
- validation history
- retry history
- failure history
- operator-visible reasoning for terminal outcomes

History MUST NOT contain secrets.

---

## Metrics (conceptual)

Extend existing platform metrics practice for:

- admission outcomes
- stage latencies
- parse outcome distribution
- progress/stall/timeout counts
- publish completions / exactly-once no-ops
- orphan recoveries
- capacity claim leaks (should be zero)
- workload-class utilization (interactive protection)

---

## Failure ownership values

`user_input` | `document_quality` | `external_dependency` | `platform` | `operator_action`
