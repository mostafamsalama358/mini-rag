# Contract: Admission, Capacity & Service Protection

**Feature**: 017-scalability-reliability | **Version**: 1.0.0  
**Normative for**: Application (Ingest) admission + capacity accounting

---

## Purpose

Define admission outcomes, guarantees for Accepted work, workload isolation, service protection, back-pressure, and reclamation.

---

## Admission outcomes

| Outcome | Meaning |
| ------- | ------- |
| **Accept** | Job enters `Accepted` with bounded capacity claim and processing eligibility |
| **Delay** | Explicit back-pressure; work not started; client/operator sees capacity signal |
| **Reject** | Explicit capacity/policy failure; no job capacity claim retained |

Silent accept-into-unbounded-queue is forbidden.

---

## Accepted guarantees

When a job is `Accepted`:

1. It has **processing eligibility** under current operational mode and component health.
2. It holds a **bounded capacity claim** for its workload class until reclamation.
3. It MUST progress, wait visibly, stall-escalate, or reach a terminal state — not disappear.
4. Acceptance is **not** an unbounded resource promise.

---

## Workload classes

At minimum:

- small documents
- large documents
- background maintenance
- migration

Isolation: one class MUST NOT consume all platform capacity.

---

## Service protection

Interactive ingestion capacity MUST remain usable for interactive admission and progress. Background processing, maintenance, and migration MUST NOT consume resources required for that interactive capacity.

---

## Stage flow control

Slow downstream stages MUST regulate upstream production (admission and intra-job stage progress) so buffers remain bounded.

---

## Resource reclamation

Capacity claims and reclaimable intermediate artifacts MUST be released after:

- cancellation
- timeout
- permanent failure
- worker restart recovery
- worker crash orphan recovery

Indefinite leaks are platform failures (failure ownership: `platform`).

---

## Scheduling objectives (non-algorithmic)

- Fairness across tenants/projects
- Starvation prevention
- Workload prioritization among declared classes
- Predictable allocation under steady load
