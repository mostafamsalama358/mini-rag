# Contract: Ingest Stage Contracts

**Feature**: 017-scalability-reliability | **Version**: 1.0.0  
**Normative for**: stage owners under Application (Ingest) orchestration

---

## Purpose

Define accepted input, produced output, failure contract, and completion contract per major stage. Prevents silent semantic drift and accidental publish outside Publishing.

---

## Shared rules

1. Only **Publishing** may change Active Version visibility.
2. Stages MUST honor stage flow control (slow downstream regulates upstream).
3. Failures MUST set failure ownership and retry eligibility.
4. Completion MAY emit a checkpoint when the stage is designated resumable.
5. Secrets MUST NOT appear in stage outputs or history details.

---

## Admission / Validation

| Element | Contract |
| ------- | -------- |
| **Accepted input** | Submission intent: tenant, logical document identity, content reference, workload class hints |
| **Produced output** | Job in `Accepted`→`Validating` with capacity claim; authorization/tenant/policy/size gates evaluated |
| **Failure** | Security/policy/validation/capacity → explicit reject or `Failed`; ownership `user_input` or capacity signal; no expensive work |
| **Completion** | Job eligible to enter Parsing with validated configuration version |

---

## Parsing

| Element | Contract |
| ------- | -------- |
| **Accepted input** | Validated content reference; budgets; configuration version |
| **Produced output** | Structured document representation (006 Document Model lineage) + Parse Outcome (`success`/`degraded`/`failed`) |
| **Failure** | `failed` outcome or dependency unavailable → fail fast or defer per health/circuit; ownership document_quality or external_dependency |
| **Completion** | Transition to Chunk Preparation only if minimum usable content gate passes (degraded path → `Degraded Parsing` then gate) |

---

## Chunk Preparation

| Element | Contract |
| ------- | -------- |
| **Accepted input** | Document Model (or degraded equivalent) passing post-parse gates |
| **Produced output** | Bounded chunk preparation units (unpublished) within memory budget |
| **Failure** | Budget/structural failure → `Failed`; ownership platform or document_quality |
| **Completion** | Units ready for Enrichment; optional checkpoint |

---

## Enrichment

| Element | Contract |
| ------- | -------- |
| **Accepted input** | Prepared chunk units; embedding/enrichment dependency Healthy or acceptable Degraded |
| **Produced output** | Enriched unpublished batch units under in-flight batch limits |
| **Failure** | Dependency/circuit → fail fast/defer; ownership external_dependency; no Active Version change |
| **Completion** | Batches ready for Indexing; checkpoints allowed on durable batch progress |

---

## Indexing

| Element | Contract |
| ------- | -------- |
| **Accepted input** | Enriched unpublished batches |
| **Produced output** | Index materialization **not** yet Active |
| **Failure** | Storage/DB issues → fail fast/defer/cleanup; ownership external_dependency or platform |
| **Completion** | Material ready for Publishing integrity gates; still invisible as Active Version |

---

## Publishing

| Element | Contract |
| ------- | -------- |
| **Accepted input** | Unpublished material + integrity evidence for the version |
| **Produced output** | Exactly-once Publish Completion; Active Version switch; fully committed predicates true |
| **Failure** | Integrity fail → `Failed`; Active Version unchanged; ownership document_quality or platform |
| **Completion** | Job → `Completed` or `Completed With Warnings`; prior version superseded if present |
