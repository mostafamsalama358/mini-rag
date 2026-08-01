# Contract: Operational Modes & Component Health

**Feature**: 017-scalability-reliability | **Version**: 1.0.0  
**Normative for**: Application (Ingest) orchestration + operators

---

## Purpose

Separate **platform operating posture** from per-component health, and define expected behavior in each mode.

---

## Component health (per stage / dependency)

| State | Meaning |
| ----- | ------- |
| `Healthy` | Stage/dependency usable for normal processing |
| `Degraded` | Impaired but usable under restricted/degraded outcomes |
| `Unavailable` | Must not be relied on; fail fast or defer dependent work |

Dependencies in scope: parser, OCR, embedding, storage, database, LLM/generation (if used).

Circuit behavior: repeated failures eventually fail-fast until health returns to Healthy or acceptable Degraded.

---

## Operational modes

| Mode | Admission | Processing |
| ---- | --------- | ---------- |
| **Normal** | Within capacity: accept / delay / reject as usual | Full stage processing under health |
| **Degraded** | May tighten admission | Continue with explicit degraded/fail-fast paths; never silent corruption |
| **Maintenance** | Often delayed/restricted | In-flight drain/complete/cancel per policy with cleanup |
| **Recovery** | May be tightened until recovery objectives met | Orphan detect/resume/reclaim and consistency restoration prioritized |
| **Admission Restricted** | New work delayed or rejected with mode/capacity signal | Accepted in-flight work continues under limits |

---

## Observability

- Mode changes MUST be observable.
- Jobs MUST record mode-at-admit; mode effects that alter outcomes MUST appear in operational history.
- Health and mode jointly drive orchestration decisions; neither alone is sufficient for maintenance/recovery postures.
