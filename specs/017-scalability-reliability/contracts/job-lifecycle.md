# Contract: Ingest Job Lifecycle

**Feature**: 017-scalability-reliability | **Version**: 1.0.0  
**Normative for**: Application (Ingest) orchestration

---

## Purpose

Define explicit, observable lifecycle states and legal transitions for every Ingest Job.

---

## States

| State | Kind | Meaning |
| ----- | ---- | ------- |
| `Accepted` | Non-terminal | Job identity assigned; bounded capacity claim established |
| `Validating` | Non-terminal | Security, policy, size/type, capacity checks |
| `Parsing` | Non-terminal | Bounded/streaming parse (full-quality path) |
| `Degraded Parsing` | Non-terminal | Parse under degraded quality mode |
| `Chunk Preparation` | Non-terminal | Structure → chunk preparation within budgets |
| `Enrichment` | Non-terminal | Batched enrichment (unpublished) |
| `Indexing` | Non-terminal | Batched index materialization (unpublished) |
| `Publishing` | Non-terminal | Integrity gates + exactly-once Active Version activation |
| `Completed` | Terminal | Fully committed; no warnings |
| `Completed With Warnings` | Terminal | Fully committed with non-fatal warnings |
| `Failed` | Terminal | Explicit failure; Active Version unchanged |
| `Cancelled` | Terminal | Operator/shutdown cancel after cleanup |
| `Timed Out` | Terminal | Timeout after cleanup |

---

## Transition rules

1. Every transition MUST append an Operational History Event with timestamp, stage, and cause.
2. Terminal states are irreversible for the same `job_id`.
3. Only `Publishing` may produce a Publish Completion.
4. `Completed` / `Completed With Warnings` REQUIRE successful Publish Completion and integrity gate pass.
5. `Completed With Warnings` is reserved for non-fatal quality warnings (e.g., degraded parse) after successful publish.
6. Cancellation/timeout MAY interrupt any non-terminal state except that an in-flight atomic publish already past the point of no return MUST complete deterministically (exactly-once) rather than half-apply.

---

## Progress kinds (orthogonal to state)

| Kind | Meaning |
| ---- | ------- |
| `progressing` | Meaningful stage progress observed |
| `waiting` | Blocked on back-pressure or dependency; not stalled |
| `stalled` | No-progress detected; escalation toward timeout |

---

## Consumer expectations

- Operators reconstruct path via `correlation_id` + history.
- Clients MAY poll job status; terminal states are final for that job identity.
- New attempts use a new job (and same or new version per idempotency rules).
