# Research: Production Scalability & Reliability

**Feature**: `017-scalability-reliability` | **Date**: 2026-07-18  
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

All Technical Context unknowns resolved. Decisions are architectural/behavioral; concrete thresholds remain configuration chosen at implementation from measured baselines.

---

## R1 — Sole-path hardening vs new ingest stack

**Decision**: Harden the existing Application (Ingest) → Document Intelligence → Chunking → Persist/Index path. Do not introduce a second selectable production ingest implementation.

**Rationale**: Spec NFR-008 and 016 M0 freeze forbid parallel production stacks for the same concern. Scalability/reliability properties attach to the sole owner path.

**Alternatives considered**:
- Greenfield ingest stack behind a feature flag — rejected (AP8 / dual-path growth).
- Shadow-only forever without cutover — rejected (does not deliver production guarantees).

---

## R2 — Durable Ingest Job control plane

**Decision**: Persist explicit Ingest Job lifecycle, correlation identity, checkpoints, publish completion, failure ownership, and operational history in PostgreSQL alongside existing task execution records. Celery remains the execution vehicle; job state is the source of truth for lifecycle/terminal outcomes.

**Rationale**: Spec requires observable transitions, resume eligibility, orphan recovery, and audit reconstruction. Ephemeral worker memory cannot own these guarantees.

**Alternatives considered**:
- Celery result backend alone as lifecycle authority — rejected (insufficient for versioned publish, orphans, audit completeness).
- External workflow engine — rejected for v1 (unnecessary stack expansion; constitution prefers existing Celery placement).

---

## R3 — Atomic + exactly-once publishing

**Decision**: Prepare searchable material for a Logical Document Version off the active path; activate Active Version in a single deterministic publish completion. Retries/duplicate completion signals after successful activation are no-ops with respect to publish.

**Rationale**: Spec FR-033/FR-052 and SC-011/SC-018 require no partial visibility and exactly one activation per version.

**Alternatives considered**:
- In-place overwrite of searchable units during indexing — rejected (partial visibility window).
- Dual-active versions during cutover — rejected (breaks FR-034).

---

## R4 — Logical document identity and version

**Decision**: Idempotency unit is `(Logical Document Identity, Logical Document Version)`. Identity maps to the platform’s existing asset/document identity; version advances on content replacement. At most one Active Version per identity.

**Rationale**: Spec FR-012/FR-034/FR-035. Aligns with existing asset-centric ingest without inventing a parallel identity system.

**Alternatives considered**:
- Identity-only idempotency (no version) — rejected (cannot express safe replacement).
- Content-hash-only identity — deferred as optional fingerprint within version metadata; not required as the sole key.

---

## R5 — Streaming / memory-bounded processing

**Decision**: Process content in bounded units through parse → chunk preparation → batched enrichment/indexing. Peak memory governed by workload-class budgets, not full document size (within hard max).

**Rationale**: Spec FR-002/FR-004/SC-001. Builds on 006 large-table batching research without redefining Document Model vocabulary.

**Alternatives considered**:
- Full in-memory Document Model for all sizes — rejected for large-document profile.
- Spilling to ad hoc temp files without checkpoint semantics — rejected (orphans/leaks).

---

## R6 — Checkpoint & resume vs full restart

**Decision**: Support restart-safe checkpoints at least after durable parse progress and durable pre-publish batch progress. Resume-eligible jobs continue; others fail explicitly or await operator disposition. Resume never bypasses security/integrity gates or exactly-once publish.

**Rationale**: Spec FR-030–FR-032, SC-013.

**Alternatives considered**:
- Always restart from zero on worker loss — rejected for large docs (waste + longer inconsistency windows).
- Fine-grained per-token checkpoints — rejected as premature complexity for v1.

---

## R7 — Degraded parsing vs fail-fast

**Decision**: Keep 006 outcome model (`success` / `degraded` / `failed`). Degraded may publish only if minimum usable-content + integrity gates pass → terminal `Completed With Warnings`. Empty or unsafe outcomes never succeed.

**Rationale**: Spec FR-007–FR-010/FR-026; preserves 006 semantics while adding lifecycle terminal clarity.

**Alternatives considered**:
- Always fail on any structural loss — rejected (too brittle for production corpora).
- Always degrade to success without warnings — rejected (hides quality).

---

## R8 — Admission, capacity, and service protection

**Decision**: Admission is capacity-based (accept / delay / reject). `Accepted` carries a bounded capacity claim until reclamation. Isolate workload classes; protect interactive ingestion capacity from background/maintenance/migration.

**Rationale**: Spec FR-006/FR-044/FR-054/FR-055, SC-002/SC-021.

**Alternatives considered**:
- Unbounded queue with best-effort workers — rejected (silent collapse risk).
- Single global concurrency without classes — rejected (large-doc starvation of interactive/small).

---

## R9 — Dependency isolation and circuits

**Decision**: Model parser/OCR/embedding/storage/database/(optional) LLM as dependencies with Healthy/Degraded/Unavailable and circuit-open fail-fast/defer behavior. Prevent cascading unbounded retries.

**Rationale**: Spec FR-039–FR-041, SC-015. Aligns with constitution provider isolation.

**Alternatives considered**:
- Infinite retry on all infra errors — rejected.
- Hard-down entire ingest on any dependency blip — rejected (over-broad; use modes + circuits).

---

## R10 — Orphans, reclamation, poison, dead-letter

**Decision**: Platform recovery owns orphan jobs/checkpoints/unpublished artifacts after worker loss. Terminal paths and crash paths reclaim capacity. Repeated permanent failures → poison quarantine; unrecoverable → dead-letter with retained metadata.

**Rationale**: Spec FR-036–FR-038/FR-056/FR-059, SC-019.

**Alternatives considered**:
- Manual-only cleanup — rejected (leaks under churn).
- Automatic delete of failure records — rejected (audit/diagnosis loss).

---

## R11 — Progress vs stall

**Decision**: Distinguish actively progressing, waiting (back-pressure/dependency), and stalled (no-progress). Stall escalates to timeout/control action.

**Rationale**: Spec FR-057, SC-020. Extends FR-019 beyond coarse progress display.

**Alternatives considered**:
- Wall-clock-only job timeout without progress notion — insufficient (punishes large slow docs).

---

## R12 — Operational modes

**Decision**: Support Normal, Degraded, Maintenance, Recovery, Admission Restricted with defined admission/processing expectations. Mode changes are observable.

**Rationale**: Spec FR-060. Separates platform posture from per-component health.

**Alternatives considered**:
- Component health alone without platform mode — rejected (cannot express maintenance/recovery admission policy cleanly).

---

## R13 — Consistency model / fully committed

**Decision**: Fully committed = job terminal success/warnings ∧ version is Active ∧ searchable observes that version ∧ metadata complete. Until then, previous Active Version (or none) remains visible.

**Rationale**: Spec FR-061, SC-022.

**Alternatives considered**:
- Searchable-as-soon-as-first-batch-indexed — rejected (partial publish).

---

## R14 — Failure ownership

**Decision**: Attach ownership taxonomy (user input, document quality, external dependency, platform, operator action) to every explicit failure for diagnosis.

**Rationale**: Spec FR-053. Orthogonal to transient/permanent classification.

**Alternatives considered**:
- Stage-only attribution — insufficient for ops routing.

---

## R15 — Stage contracts

**Decision**: Normative stage contracts for admission/validation, parsing, chunk preparation, enrichment, indexing, publishing (see `contracts/stage-contracts.md`). Only Publishing may change Active Version visibility.

**Rationale**: Spec FR-062; long-term maintainability under 016 sole owners.

**Alternatives considered**:
- Informal stage names only — rejected (semantic drift risk).

---

## R16 — External API surface

**Decision**: Keep existing ingest submission entrypoints stable where possible; extend job status/history visibility for lifecycle, progress, failure ownership, and terminal outcomes. Do not require Answer API changes.

**Rationale**: Minimize client breakage; operability requires inspectability (FR-048/FR-058).

**Alternatives considered**:
- New parallel ingest API product — deferred; not required for v1 guarantees if status surfaces are extended.
- No status enrichment — rejected (SC-007/SC-016 fail).

---

## R17 — Rollout governance

**Decision**: Enforce R0–R4 with explicit promotion, rollback, success, and exit criteria (spec Rollout governance). Canary by project cohort.

**Rationale**: Spec FR-021/FR-063, SC-008/SC-024.

**Alternatives considered**:
- Big-bang default-on — rejected for production risk.

---

## R18 — Configuration numeric defaults

**Decision**: Numeric budgets (size thresholds, concurrency, stall intervals, poison counts, batch sizes) are **not** fixed in this research. Implementation measures baselines and sets validated, versioned configuration (FR-049). Success criteria bind to configured budgets and relative bands.

**Rationale**: Spec Assumptions; avoids device-specific false precision in planning.

**Alternatives considered**:
- Hardcode limits in plan — rejected.
