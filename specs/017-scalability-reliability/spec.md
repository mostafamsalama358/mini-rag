# Feature Specification: Production Scalability & Reliability

**Feature Branch**: `017-scalability-reliability`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: "Design production-grade scalability and reliability improvements. Focus on: streaming ingestion, memory bounded processing, large document support, batching, async execution, parser reliability, degraded parsing, fail-fast behavior, validation gates, retry strategy, idempotency, explicit failures, observability, back-pressure, resource limits. Define: architecture, processing flow, failure handling, migration, testing, rollout. Avoid implementation details. Focus on long-term production scalability."

**Revision**: Principal-architect review (v2) — lifecycle, cancellation, checkpoint/resume, atomic/exactly-once publishing, versioned documents, poison/dead-letter, orphans, progress guarantees, dependency isolation, circuit breaking, resource isolation/service protection, operational modes, consistency model, failure ownership, admission guarantees, resource reclamation, stage contracts, fairness, capacity, stage flow control, component health, integrity, end-to-end observability, auditability, configuration safety, compatibility, recovery, security gates, rollout governance, and production testing strategy.

## Executive Summary

The platform MUST evolve document ingestion and indexing from a best-effort, memory-unbounded path into a **production-grade, memory-bounded, observable, recoverable, and failure-explicit pipeline**. Operators MUST be able to ingest large corpora and large individual documents without exhausting capacity, without silent corruption, without unbounded queue growth, and without starving other tenants. Users MUST observe either the previous searchable version or a fully completed new version—never a partial publish. Jobs MUST follow an explicit lifecycle with terminal states. Retries and resumes MUST be safe. Overload and dependency failure MUST be contained with back-pressure, isolation, and circuit protection rather than cascading into process collapse.

This feature strengthens the **existing** ingestion ownership path (document intelligence → chunking → indexing). It MUST NOT introduce a second selectable production ingestion stack. Improvements apply to the sole production ingest concern and remain compatible with Architecture Consolidation (016) dual-path freeze rules.

### Architectural Intent (WHAT, not HOW)

| Concern | Intent |
| ------- | ------ |
| **Streaming ingestion** | Accept and process document content in bounded units so the full document need not reside in memory at once. |
| **Memory-bounded processing** | Every stage operates within declared memory and concurrency budgets; exceeding budgets fails explicitly or sheds load. |
| **Large document support** | Documents above normal size remain first-class: progress is trackable, work is resumable, and completion is deterministic. |
| **Batching** | Downstream expensive work proceeds in controlled batches sized for throughput without unbounded buffering. |
| **Async execution** | Long-running ingest work leaves the interactive request path; submission returns quickly with a trackable job identity. |
| **Job lifecycle** | Every job moves through explicit, observable states with clear terminal outcomes. |
| **Cancellation** | Operator, timeout, and shutdown cancellation stop work safely without inconsistent searchable state. |
| **Checkpoint & resume** | Large-document work can resume from restart-safe progress after interruption. |
| **Atomic publishing** | Searchers never see a partially indexed document version. |
| **Exactly-once publishing** | Each logical document version is published once; retries and duplicate completions cannot create multiple publishes. |
| **Versioned document lifecycle** | Logical identity + version prevent duplicate active searchable content across replace/retry. |
| **Orphan detection & recovery** | Abandoned jobs, checkpoints, and intermediate artifacts have defined recovery ownership. |
| **Progress guarantees** | Operators can distinguish actively progressing work from stalled work; no-progress escalates. |
| **Operational modes** | Platform behavior is explicit under Normal, Degraded, Maintenance, Recovery, and Admission Restricted modes. |
| **Consistency model** | Ingest, searchable, metadata, and published-version state agree on when a version is fully committed. |
| **Stage contracts** | Each stage has defined accepted input, produced output, failure, and completion contracts. |
| **Parser reliability** | Parsing outcomes are classified (success, degraded, failed) with reasons; parsers do not hang indefinitely or crash the worker. |
| **Degraded parsing** | When structure cannot be fully recovered but usable content remains, ingest MAY continue with an explicit degraded quality signal. |
| **Fail-fast** | Invalid inputs, hard resource violations, and unrecoverable failures stop early with an explicit terminal failure—no silent empty indexes. |
| **Poison & dead-letter handling** | Repeated permanent failures stop consuming capacity; unrecoverable jobs are quarantined for operator review. |
| **Validation & integrity gates** | Pre-/post-stage and pre-publish checks block unsafe or incomplete results from becoming searchable. |
| **Security validation gates** | Authorization, tenant ownership, and policy compliance are verified before expensive processing. |
| **Retry strategy** | Transient failures retry under policy; permanent failures do not; every retry is idempotent. |
| **Idempotency** | Re-submitting or re-running the same logical document version does not create duplicate active searchable content. |
| **Explicit failures** | Failure modes are named, observable, auditable, and actionable. |
| **Dependency isolation & circuit breaking** | Downstream unavailability is contained; repeated failures fail fast until health returns. |
| **Resource isolation & fairness** | Large docs, small docs, maintenance, and migration work cannot starve each other or other tenants. |
| **Service protection** | Background, maintenance, and migration workloads never consume capacity reserved for interactive ingestion. |
| **Admission guarantees** | Accepted work carries explicit eligibility and reserved-capacity guarantees until terminal cleanup. |
| **Resource reclamation** | Reserved capacity and intermediate artifacts are always reclaimed after terminal outcomes or worker loss. |
| **Capacity management** | Admission reflects available capacity; concurrency and consumption stay bounded and predictable. |
| **Stage flow control** | Slow downstream stages regulate upstream work between pipeline stages. |
| **Component health** | Major stages expose Healthy / Degraded / Unavailable for orchestration decisions. |
| **Observability & auditability** | Lifecycle, validation, retry, and failure history are complete and operator-visible. |
| **Configuration safety** | Operational configuration is validated, version-aware, observable, and auditable. |
| **Recovery & continuity** | After interruption or infrastructure failure, work resumes or fails explicitly without corruption. |
| **Back-pressure** | When capacity is saturated, new work is delayed or rejected rather than accepted unboundedly. |
| **Resource limits** | Hard caps exist for document size, concurrent jobs, in-flight batches, parse time, and retry count. |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Large documents ingest without collapsing the service (Priority: P1)

An operator uploads a very large document (or a corpus containing several large documents). Today such work can exhaust memory or stall the service. With this feature, the system accepts the job asynchronously, processes content in bounded units, respects resource limits and workload isolation, and either completes successfully, completes with warnings, or fails explicitly—without taking down or starving other concurrent work.

**Why this priority**: Unbounded memory and capacity capture by large documents is the primary production scalability risk for ingestion.

**Independent Test**: Submit a document sized above the large-document threshold under concurrent light small-document load. Verify small-document jobs continue to make progress, peak consumption stays within the declared large-document budget, and the large job reaches an explicit terminal state.

**Acceptance Scenarios**:

1. **Given** a document larger than the normal-size threshold but within the hard maximum size, **When** ingest is submitted, **Then** the system accepts it as an async job and processes it without requiring the entire document to be held in memory at once.
2. **Given** a document that exceeds the hard maximum size or other hard resource gates, **When** ingest is submitted or validated, **Then** the job fails fast with an explicit, named failure reason and no partial searchable corruption is left behind.
3. **Given** one large-document job in progress, **When** other normal ingest jobs are submitted for other projects (within concurrency limits), **Then** those jobs continue to make progress and are not starved indefinitely or crashed by the large job.

---

### User Story 2 - Overload is absorbed with back-pressure, not silent collapse (Priority: P1)

An operator submits a burst of ingest jobs that would exceed configured concurrency, queue depth, or memory budgets. The system applies admission and stage-level back-pressure: it delays admission or rejects new work with an explicit overload signal, while already-accepted work continues under limits.

**Why this priority**: Production reliability depends on controlled admission; unbounded queues turn transient spikes into prolonged outages.

**Independent Test**: Flood the ingest admission path beyond configured limits. Verify new work is delayed or rejected with an explicit overload outcome, accepted work remains within concurrency/memory budgets, and signals show backlog and rejection rates.

**Acceptance Scenarios**:

1. **Given** concurrent in-flight ingest work already at the configured limit, **When** an additional job is submitted, **Then** the system either queues it under a bounded backlog policy or rejects it with an explicit capacity/back-pressure failure—never accepts unlimited unbounded work.
2. **Given** backlog at the configured maximum, **When** further submissions arrive, **Then** the system rejects or delays them with a clear capacity signal rather than growing memory without bound.
3. **Given** overload has subsided, **When** capacity frees, **Then** previously delayed (if any) or newly submitted work proceeds under the same limits without manual restart of the service.

---

### User Story 3 - Parsing is reliable: success, degraded, or explicit failure (Priority: P1)

A user uploads a document that is malformed, partially readable, or unusually structured. The system classifies the parse outcome. Fully successful parses proceed. Partially recoverable content proceeds under **degraded parsing** with an explicit quality signal. Unrecoverable or unsafe cases **fail fast** with a named reason. Empty “success” with zero usable content is forbidden.

**Why this priority**: Silent parse failures and empty indexes are a trust-breaking reliability defect; degraded-vs-fail-fast policy must be consistent and observable.

**Independent Test**: Run a fixed suite of fixtures: clean document, partially damaged document with recoverable text, and unrecoverable/corrupt document. Verify outcomes are success / degraded-with-signal / explicit-failure respectively, each with a reason code and no worker crash.

**Acceptance Scenarios**:

1. **Given** a well-formed supported document, **When** parsing completes, **Then** the outcome is full success and downstream stages receive a complete structural representation suitable for indexing.
2. **Given** a document where structure is incomplete but usable content can still be extracted safely, **When** parsing finishes, **Then** ingest MAY continue in degraded mode with an explicit degraded flag and reason, and searchable content is limited to what was safely recovered.
3. **Given** a document that cannot yield any safe usable content, or violates fail-fast gates, **When** parsing or validation runs, **Then** the job terminates as an explicit failure with a named reason and does not publish empty or corrupted searchable results as success.

---

### User Story 4 - Retries, resume, and cancellation leave a consistent index (Priority: P1)

Transient infrastructure faults, worker restart, operator cancellation, or timeout interrupt a job mid-flight. Resume or retry does not duplicate active searchable content. Cancellation and timeout leave searchers on the previous complete version (or no version if none existed)—never a partial new version. Permanent failures stop retrying; poison documents are quarantined.

**Why this priority**: Production ingest without idempotent retry, atomic publish, and safe cancellation creates inconsistent knowledge bases under normal operational churn.

**Independent Test**: (a) Force transient failure after partial progress, resume/retry—final active searchable content matches a single successful version. (b) Cancel mid-index—searchers never see partial new content. (c) Exhaust retries on a permanent fixture—job becomes poison/dead-letter and stops consuming capacity.

**Acceptance Scenarios**:

1. **Given** a job that failed for a classified transient reason with a restart-safe checkpoint, **When** it resumes or retries within policy, **Then** the final active searchable version is identical in logical content to a single successful run (no duplicate active units).
2. **Given** a job cancelled by an operator, by timeout, or by graceful shutdown, **When** cancellation completes, **Then** the job reaches terminal `Cancelled` or `Timed Out`, cleanup finishes, and searchable state remains consistent (previous active version or none).
3. **Given** repeated permanent failures for the same logical document version, **When** poison classification thresholds are met, **Then** the job enters quarantine/dead-letter handling and does not continuously consume processing capacity.
4. **Given** a Logical Document Version that has already published successfully, **When** a retry or duplicate completion signal arrives, **Then** no additional publish occurs and the terminal completion remains unchanged (exactly-once).

---

### User Story 5 - Searchers only see complete document versions (Priority: P1)

A document already has an active searchable version. A replacement ingest runs. Until the new version fully passes integrity and publish gates, users searching still see the previous version. When publish completes, they see only the new active version. They never observe a mix of old and new partial content.

**Why this priority**: Partial visibility of in-flight index updates destroys trust in retrieval answers.

**Independent Test**: While a replacement job is in Enrichment/Indexing/Publishing, run searches against that logical document. Results must match the previous active version until the job reaches `Completed` or `Completed With Warnings`, after which only the new active version is visible.

**Acceptance Scenarios**:

1. **Given** an active version V1 and an in-flight job for version V2, **When** users search before V2 publish completes, **Then** results reflect V1 only.
2. **Given** V2 passes all integrity and publish gates, **When** publishing completes, **Then** V2 becomes the sole active version and V1 is superseded (not concurrently active).
3. **Given** the V2 job fails, is cancelled, or times out before successful publish, **When** the job reaches a terminal non-success state, **Then** V1 remains the sole active version and no partial V2 content is searchable.

---

### User Story 6 - Operators can observe, audit, migrate, and roll out safely (Priority: P2)

Platform operators need full job history, component health, validation gates, compatibility across mixed versions during rolling upgrade, and staged rollout so they can migrate without big-bang risk. They can inspect failures, quarantine, enable progressively, and roll back if gates fail.

**Why this priority**: Long-term scalability only ships if migration, auditability, and rollout are operable.

**Independent Test**: Execute migration/rollout checklist: observability and audit history available; golden corpus gates; canary cohort; mixed-version worker coexistence validated; rollback without unrelated feature impact; poison/dead-letter inspection path exercised.

**Acceptance Scenarios**:

1. **Given** the scalable ingest path is enabled for a canary project set, **When** the golden corpus is processed, **Then** validation and integrity gates pass (or explicitly fail with actionable reasons) before broader rollout.
2. **Given** a regression in canary metrics (failure rate, memory overruns, duplicate active content, partial publish), **When** operators trigger rollback, **Then** new ingest for those projects returns to the previous controlled behavior without requiring unrelated capability rollback.
3. **Given** any terminal or in-flight job, **When** an operator inspects it, **Then** they see lifecycle history, validation history, retry history, failure history, and operator-visible reasoning sufficient to decide retry, discard, or escalate.

---

### Edge Cases

- Document exactly at the large-document threshold vs just above the hard maximum size.
- Empty file, zero-byte upload, or content that parses to zero elements after “success.”
- Duplicate submission of the same logical document version while a prior job is still running.
- Replacement submission creating a new logical document version while prior version remains active.
- Worker crash mid-batch: resume from checkpoint or safe re-run without duplicate active content.
- Cancellation during Publishing: atomicity preserved; previous active version remains.
- Degraded parse that later fails a post-stage or integrity gate.
- Burst of many tiny documents vs few huge documents under isolated budgets (no starvation).
- Parse time exceeding deadline → `Timed Out` with cleanup.
- Downstream stage slower than upstream → stage flow control regulates upstream.
- Dependency Unavailable with circuit open → fail fast / defer without cascading.
- Poison document re-submitted after quarantine without operator clearance.
- Mixed-version workers during rolling deployment processing the same job family.
- Partial corpus ingest where some documents succeed, some complete with warnings, some fail—per-document outcomes preserved.
- Configuration change mid-flight: in-flight jobs remain consistent with a validated configuration version.
- Publish stage retried after successful activation: no second publish; terminal completion remains deterministic.
- Orphan job/checkpoint/artifacts after abrupt worker loss: recovery ownership reclaims or resumes without leak.
- Actively slow large document vs stalled job with no progress: operators can distinguish; stall escalates to timeout.
- Background/migration load at peak: interactive ingestion admission and progress remain within protected capacity.
- Platform in Admission Restricted or Maintenance mode: expected admission/processing behavior is explicit.

## Requirements *(mandatory)*

### Functional Requirements

#### Architecture & processing flow

- **FR-001**: System MUST provide a single production ingestion processing flow with explicit stage boundaries for observability and failure attribution, aligned to the Job Lifecycle states defined in this specification.
- **FR-002**: System MUST process document content in streaming or chunked bounded units such that peak memory for a job is governed by configured budgets, not by full document size alone (within the hard maximum size).
- **FR-003**: System MUST execute long-running ingest work asynchronously relative to the interactive submission path; submission MUST return a trackable job identity promptly.
- **FR-004**: System MUST apply batching to expensive downstream stages under configured batch size and in-flight batch limits.
- **FR-005**: System MUST enforce resource limits for at least: maximum document size, maximum concurrent jobs per capacity class, maximum bounded backlog, maximum parse duration, maximum job duration, and maximum retry attempts.
- **FR-006**: System MUST apply admission back-pressure when concurrency or backlog limits are reached, by delaying admission under policy or rejecting with an explicit capacity failure.

#### Job lifecycle

- **FR-023**: Every Ingest Job MUST progress through an explicit lifecycle including at least the states: `Accepted`, `Validating`, `Parsing`, `Degraded Parsing`, `Chunk Preparation`, `Enrichment`, `Indexing`, `Publishing`, `Completed`, `Completed With Warnings`, `Failed`, `Cancelled`, `Timed Out`.
- **FR-024**: `Completed`, `Completed With Warnings`, `Failed`, `Cancelled`, and `Timed Out` MUST be terminal states; once entered, the job MUST NOT leave them except via a new job for a new attempt/version under idempotency rules.
- **FR-025**: Every lifecycle transition MUST be observable (timestamped history) and attributable to a stage or control action (admission, gate, dependency, operator, timeout, shutdown).
- **FR-026**: `Completed With Warnings` MUST be used when the job publishes safely under degraded parsing or other non-fatal quality warnings; it MUST NOT be used when integrity or publish gates fail.

#### Cancellation

- **FR-027**: System MUST support cancellation initiated by: operator action, job/stage timeout, and graceful shutdown of processing capacity.
- **FR-028**: Cancellation MUST transition the job to `Cancelled` or `Timed Out` (as applicable) only after safe cleanup; searchable state MUST remain consistent (previous active version or none—never a partial new version).
- **FR-029**: Cancelled or timed-out work MUST release reserved capacity and MUST NOT continue expensive downstream stages after cancellation is acknowledged.

#### Checkpoint & resume

- **FR-030**: Large-document processing MUST support resumable execution across designated resumable stages (at minimum after parse progress and after durable batch progress in enrichment/indexing preparation).
- **FR-031**: Checkpoints MUST be restart-safe: after worker loss, a job that is resume-eligible MUST continue from the last committed checkpoint or fail explicitly—never publish from ambiguous partial progress.
- **FR-032**: Resume eligibility MUST be defined (checkpoint present, dependency health allows, not cancelled/poisoned/dead-lettered, within retry/time policy).

#### Atomic publishing & versioned documents

- **FR-033**: Publishing MUST be atomic with respect to search visibility: observers MUST see either the previous active version or the fully completed new version—never a partially published state.
- **FR-034**: System MUST model **Logical Document Identity**, **Logical Document Version**, **Active Version**, and **Superseded Version**, and MUST ensure at most one active searchable version per logical document identity at a time.
- **FR-035**: Replacement lifecycle MUST supersede the prior active version only upon successful publish of the new version; failed/cancelled/timed-out replacements MUST leave the prior active version unchanged.
- **FR-012**: System MUST make ingest idempotent with respect to logical document identity **and** logical document version: retries, resumes, and duplicate submissions MUST NOT create duplicate active searchable content for the same version.
- **FR-052**: Each Logical Document Version MUST be published **exactly once**: retries, resumes, and duplicate completion signals MUST NOT cause additional publish operations; publish completion MUST be deterministic (at most one successful activation per version).

#### Parser reliability & quality modes

- **FR-007**: System MUST classify every parse outcome as one of: `success`, `degraded`, or `failed`, and MUST expose the classification with a reason code.
- **FR-008**: System MUST allow degraded parsing to proceed only when a minimum usable-content gate passes; otherwise it MUST fail explicitly. Jobs that publish under degraded parsing MUST terminate as `Completed With Warnings` when all other gates pass.
- **FR-009**: System MUST fail fast (no further stage advancement toward publish) when pre-stage validation fails, hard resource limits are violated, parse outcome is `failed`, integrity gates fail, or security gates fail.
- **FR-010**: System MUST NOT report `Completed` or `Completed With Warnings` when no safe searchable content was produced for the new version.

#### Poison documents & dead-letter handling

- **FR-036**: System MUST classify a logical document version as a **poison document** when permanent failures repeat beyond policy, and MUST divert it to a quarantine flow that stops automatic capacity consumption.
- **FR-037**: Quarantined/poison work MUST remain inspectable by operators, with a defined path to clear for retry, discard, or mark terminal.
- **FR-038**: Unrecoverable jobs MUST be placeable in a **dead-letter** destination retaining failure metadata sufficient for operator inspection, recovery attempt, or discard—without silent loss of the failure record.

#### Failure handling & retries

- **FR-011**: System MUST distinguish transient vs permanent failure classes and apply retry only to transient classes under a bounded retry policy (count and/or time).
- **FR-013**: System MUST surface explicit failure information including failure class, **failure ownership**, reason, stage, job identity, correlation identity, and logical document identity/version.
- **FR-014**: System MUST define cleanup or compensation so a failed, cancelled, timed-out, or superseded run does not leave contradictory **active** searchable state for that logical document identity.
- **FR-053**: Failure ownership MUST classify origin as one of: **user input**, **document quality**, **external dependency**, **platform**, or **operator action**, to support operational diagnosis without conflating causes.

#### Dependency isolation & circuit breaking

- **FR-039**: System MUST isolate failures of major dependencies so that unavailability of parser, OCR, embedding, storage, database, or generation/LLM services does not cascade into unbounded retries, unbounded backlog growth, or process collapse.
- **FR-040**: When a dependency is Unavailable or circuit-open, new work requiring that dependency MUST fail fast or defer under capacity policy; already-running work MUST follow cancellation/timeout/cleanup rules rather than hang indefinitely.
- **FR-041**: Architecture MUST support circuit breaking: repeated downstream failures MUST eventually cause fail-fast behavior for that dependency until health returns to Healthy (or acceptable Degraded).

#### Resource isolation, scheduling & capacity

- **FR-042**: System MUST isolate capacity across workload classes including at least: small documents, large documents, background maintenance, and migration work, such that one class cannot consume all processing capacity.
- **FR-043**: Scheduling objectives MUST include fairness across tenants/projects, starvation prevention, workload prioritization among declared classes, and predictable resource allocation—without requiring a specific scheduling algorithm in this specification.
- **FR-044**: Admission MUST be based on available capacity (not only static counts): controlled concurrency and bounded resource consumption MUST yield predictable throughput under steady load.
- **FR-045**: Back-pressure MUST exist between internal processing stages so that a slow downstream stage naturally regulates upstream production within the job and across the pipeline.
- **FR-054**: **Service protection**: background processing, maintenance, and migration workloads MUST NOT consume resources required to sustain interactive ingestion admission and progress within declared interactive capacity.
- **FR-055**: **Admission guarantees**: when a job reaches `Accepted`, architecture MUST imply explicit processing eligibility and reserved capacity (or an equivalently bounded claim on capacity) until the job reaches a terminal state and reclamation completes; acceptance MUST NOT mean unbounded or unguaranteed work.
- **FR-056**: **Resource reclamation**: reserved capacity and reclaimable intermediate artifacts MUST be released after cancellation, timeout, permanent failure, worker restart, and worker crash such that reserved resources do not leak indefinitely.

#### Component health

- **FR-046**: Each major stage (admission, validation, parsing, chunk preparation, enrichment, indexing, publishing) MUST expose a component health state of `Healthy`, `Degraded`, or `Unavailable` for orchestration and admission decisions.

#### Validation, integrity & security gates

- **FR-015**: System MUST enforce admission/validation gates before expensive work, including type/size/policy checks, capacity checks, **authorization**, **tenant ownership**, and **policy compliance**.
- **FR-016**: System MUST enforce post-parse and pre-publish validation gates (minimum content, structural sanity, idempotency/version identity presence, degraded-mode eligibility).
- **FR-017**: Validation gate failures MUST be explicit and MUST block publishing as `Completed` or `Completed With Warnings`.
- **FR-047**: Before publish, integrity gates MUST verify produced content, searchable output completeness, metadata completeness, and consistency between logical document version and material to be activated; publish MUST occur only after these gates pass.

#### Observability & auditability

- **FR-018**: System MUST emit structured operational signals for: job lifecycle states and transitions, stage latency, parse outcome counts, retry counts, cancellation/timeout events, back-pressure/admission rejections, circuit/dependency health, poison/dead-letter events, orphan recovery events, progress/stall signals, operational mode, and resource-limit violations—each correlatable by job and project.
- **FR-019**: System MUST make per-job progress observable for large documents (lifecycle state, stage, and coarse progress) so operators can distinguish actively progressing work, work waiting on back-pressure/dependency, and stalled work.
- **FR-048**: Every Ingest Job MUST retain a complete operational history including lifecycle history, validation history, retry history, failure history, and operator-visible reasoning for terminal outcomes.
- **FR-057**: **Progress guarantees**: architecture MUST define actively progressing vs stalled work, detect no-progress conditions, and escalate stalls to timeout (or equivalent terminal/control action) so operators can distinguish slow work from stuck work.
- **FR-058**: **End-to-end observability**: a single correlation identity MUST allow operators to reconstruct complete job history from admission through every processing stage to terminal completion (or failure/cancel/timeout), without gaps in stage coverage.

#### Configuration safety

- **FR-049**: Operational configuration affecting ingest behavior MUST be validated before use, version-aware, observable, and auditable; unsafe or invalid configuration MUST NOT be applied silently.

#### Orphans, modes, consistency & stage contracts

- **FR-059**: Architecture MUST detect and recover **orphan** jobs, orphan checkpoints, and orphan intermediate artifacts left by abandoned processing after worker failure; every orphaned state MUST have defined recovery ownership (resume, reclaim, fail explicitly, or operator disposition).
- **FR-060**: System MUST support explicit **operational modes** including at least: `Normal`, `Degraded`, `Maintenance`, `Recovery`, and `Admission Restricted`, each with defined expected admission and processing behavior.
- **FR-061**: Architecture MUST define a **consistency model** relating ingestion state, searchable state, metadata state, and published document version, including when a Logical Document Version is **fully committed** (safe for searchers and durable against restart).
- **FR-062**: Each major processing stage MUST have an architectural **stage contract** defining accepted input, produced output, failure contract, and completion contract, so stage boundaries remain maintainable without silent semantic drift.

#### Migration, compatibility, testing, rollout

- **FR-020**: System MUST define a migration path from current ingest behavior to the scalable path that preserves existing successful corpus semantics for a documented golden set (parity within agreed tolerances for degraded-mode / completed-with-warnings cases).
- **FR-021**: System MUST support staged rollout (e.g., project allowlist or percentage) and rollback of the scalable-path enablement without requiring unrelated feature rollback.
- **FR-022**: System MUST provide a testable golden corpus covering: normal docs, large docs, corrupt/degraded fixtures, overload admission, idempotent retry, cancellation, resume after restart, and atomic publish under replacement.
- **FR-050**: Migration and rollout MUST support forward compatibility, backward compatibility, rolling deployment compatibility, and mixed-version worker compatibility so gradual production upgrades remain safe.
- **FR-051**: Architecture MUST define recovery expectations: after processing capacity restart or infrastructure interruption, in-flight resume-eligible work continues from checkpoint or reaches an explicit terminal failure; service continuity for admission decisions MUST be preserved when capacity allows.
- **FR-063**: **Rollout governance**: progressive rollout MUST define measurable promotion criteria, rollback criteria, rollout success gates, and phase exit criteria so expansion remains reversible and evidence-based.

### Key Entities

- **Ingest Job**: Trackable asynchronous work unit for one logical document version (or defined batch unit), with lifecycle state, correlation identity, terminal outcome, and operational history.
- **Job Lifecycle State**: One of the explicit states in FR-023; includes non-terminal processing states and terminal outcomes.
- **Logical Document Identity**: Stable identity of a document across replacements and retries.
- **Logical Document Version**: Immutable version under a logical identity; unit of idempotency for a content revision.
- **Active Version**: The single version currently visible to search for a logical identity.
- **Superseded Version**: A formerly active version replaced by a newer successfully published version.
- **Parse Outcome**: Classification (`success` / `degraded` / `failed`) plus reason code and optional quality notes.
- **Checkpoint**: Restart-safe record of committed progress enabling resume eligibility.
- **Poison Document**: Logical document version diverted to quarantine after repeated permanent failures.
- **Dead-Letter Record**: Retained unrecoverable job failure metadata for operator inspection, recovery, or discard.
- **Resource Budget**: Declared limits for memory-related processing units, concurrency, backlog, document size, durations, and retries—optionally per workload class.
- **Workload Class**: Capacity isolation category (e.g., small document, large document, background maintenance, migration).
- **Component Health**: `Healthy` / `Degraded` / `Unavailable` for a major stage or dependency.
- **Validation Gate Result**: Pass/fail of an admission, mid-pipeline, integrity, or security check, with reason.
- **Back-Pressure Signal**: Explicit indication that admission or stage progress is delayed or rejected due to capacity.
- **Batch Unit**: Bounded group of work items in a downstream expensive stage.
- **Configuration Version**: Validated, auditable snapshot of operational ingest configuration in effect.
- **Rollout Cohort**: Set of projects or traffic fraction enabled for the scalable path during migration.
- **Publish Completion**: Deterministic, exactly-once activation outcome for a Logical Document Version.
- **Orphan**: Job, checkpoint, or intermediate artifact lacking an active owner after abandonment or worker loss.
- **Progress Signal**: Indication that work is actively progressing, waiting (back-pressure/dependency), or stalled (no-progress).
- **Operational Mode**: Platform-wide operating posture (`Normal`, `Degraded`, `Maintenance`, `Recovery`, `Admission Restricted`).
- **Fully Committed Version**: Logical Document Version whose ingest, metadata, and searchable states agree under the consistency model after successful publish.
- **Stage Contract**: Architectural definition of a stage’s accepted input, produced output, failure contract, and completion contract.
- **Failure Ownership**: Origin classification of a failure (user input, document quality, external dependency, platform, operator action).
- **Interactive Ingestion Capacity**: Capacity reserved/protected for interactive ingest admission and progress against background/maintenance/migration consumption.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture layer boundaries and feature-first organization.
- **NFR-002**: I/O-bound ingest stages MUST be async-first; blocking work MUST be isolated from the interactive request path.
- **NFR-003**: Ingestion and indexing MUST remain idempotent under retry and resume (Constitution VI).
- **NFR-004**: Structured logging MUST include correlation identities at service and job boundaries (Constitution VIII).
- **NFR-005**: Unit and integration tests MUST cover new/changed reliability and scalability behaviors (Constitution VII).
- **NFR-006**: Secrets MUST NOT appear in logs, audit history, or source control; upload validation and size limits remain enforced (Constitution IX).
- **NFR-007**: Long-running parse/embed/index work MUST NOT run on the interactive request path budget (Constitution X).
- **NFR-008**: This feature MUST NOT introduce a parallel selectable production ingestion stack; it strengthens the sole production ingest owner (016 M0 freeze).
- **NFR-009**: Observability for new stages MUST be queryable in the same operational practice as existing pipeline metrics (extend, do not invent an opaque side channel).
- **NFR-010**: Security validation gates MUST run before expensive processing; tenant boundaries MUST NOT be bypassable by retry, resume, or migration workloads.

## Job Lifecycle *(mandatory for this feature)*

| State | Kind | Meaning |
| ----- | ---- | ------- |
| **Accepted** | Non-terminal | Job identity assigned; awaiting or entering validation under capacity policy |
| **Validating** | Non-terminal | Security, policy, size/type, and admission checks in progress |
| **Parsing** | Non-terminal | Bounded/streaming parse in progress (full-quality path) |
| **Degraded Parsing** | Non-terminal | Parse continuing or completed under degraded quality mode |
| **Chunk Preparation** | Non-terminal | Structure normalization / chunk preparation within memory budgets |
| **Enrichment** | Non-terminal | Batched enrichment work (e.g., representation preparation) under in-flight limits |
| **Indexing** | Non-terminal | Batched index materialization; not yet atomically published |
| **Publishing** | Non-terminal | Integrity gates and atomic activation of the new version |
| **Completed** | Terminal | New version fully published; no warnings requiring operator attention |
| **Completed With Warnings** | Terminal | New version fully published with explicit non-fatal warnings (e.g., degraded parse) |
| **Failed** | Terminal | Explicit failure; no new active version published |
| **Cancelled** | Terminal | Stopped by operator or graceful shutdown cancellation after safe cleanup |
| **Timed Out** | Terminal | Stopped by timeout policy after safe cleanup |

Transitions MUST be recorded. Illegal skips that would publish without integrity gates MUST be impossible by architecture (publish only from `Publishing` after gates pass).

## Processing Flow *(mandatory for this feature)*

High-level flow (behavioral; not an implementation design):

1. **Submit** — Client/operator submits a document; system assigns job identity → `Accepted`, or returns explicit admission failure.
2. **Admit & secure** — Capacity, authorization, tenant ownership, and policy gates → `Validating`; back-pressure may delay or reject.
3. **Validate (pre)** — Size, type, hard limits, configuration version applicability; fail fast → `Failed` on violation.
4. **Parse (streaming/bounded)** → `Parsing` or `Degraded Parsing`; outcome classified; checkpoints as progress commits.
5. **Validate (post-parse)** — Minimum usable content; degraded eligibility; structural sanity.
6. **Chunk preparation** → `Chunk Preparation` within memory budgets; stage flow control if downstream is slow.
7. **Enrich** → `Enrichment` in controlled batches; dependency health/circuits observed.
8. **Index (unpublished)** → `Indexing`; materialization not yet searchable as the active version.
9. **Integrity & publish** → `Publishing`; integrity gates; atomic switch of Active Version.
10. **Complete** — `Completed` or `Completed With Warnings`; or terminal `Failed` / `Cancelled` / `Timed Out` with cleanup.
11. **Poison / dead-letter** — On repeated permanent failure or unrecoverable terminal cases, quarantine/dead-letter instead of hot-looping capacity.

## Cancellation *(mandatory for this feature)*

| Source | Expected terminal state | Searchable outcome |
| ------ | ---------------------- | ------------------ |
| Operator initiated | `Cancelled` | Previous active version (or none); no partial new version |
| Timeout | `Timed Out` | Same |
| Graceful shutdown | `Cancelled` (or resume-eligible pause then continue per recovery rules) | Same; in-flight work either resumes later or cancels with cleanup |

Cancellation MUST be acknowledged in operational history. Cleanup MUST release capacity and discard unpublished material for the in-flight version.

## Checkpoint & Resume *(mandatory for this feature)*

- Resumable stages are those that can commit restart-safe progress without exposing partial active search state (parse progress and durable pre-publish batch progress at minimum).
- After worker restart, resume-eligible jobs continue from the last checkpoint; non-eligible jobs fail explicitly or await operator action.
- Resume MUST honor cancellation, poison, dead-letter, circuit-open, and retry policy constraints.
- Resume MUST NOT bypass security or integrity gates.

## Atomic Publishing & Version Lifecycle *(mandatory for this feature)*

- **Visibility rule**: For any logical document identity, search observes either the current Active Version or, after successful publish, the new Active Version—never a blend.
- **Exactly-once publish**: Activation of a Logical Document Version occurs at most once; retries, resumes, and duplicate completion events do not create additional publish operations; publish completion is deterministic.
- **Replacement**: New Logical Document Version is prepared off the active path; activation is a single publish transition.
- **Failure/cancel/timeout before publish**: Active Version unchanged; unpublished material not searchable.
- **Idempotency unit**: Logical Document Identity + Logical Document Version.

## Consistency Model *(mandatory for this feature)*

A Logical Document Version is **fully committed** only when all of the following hold together:

1. **Ingestion state** — owning Ingest Job is terminal `Completed` or `Completed With Warnings`.
2. **Published document version** — the version is the Active Version (or correctly recorded as such for that identity).
3. **Searchable state** — search observes that Active Version’s content (not unpublished material).
4. **Metadata state** — metadata required for retrieval/citation completeness agrees with the published version.

Until fully committed, searchers continue to observe the previous Active Version (or none). After worker restart, a version is either fully committed, still in-flight under resume/orphan recovery, or explicitly not active—never an ambiguous half-committed state.

## Orphan Detection & Recovery *(mandatory for this feature)*

| Orphan type | Recovery ownership intent |
| ----------- | ------------------------- |
| **Orphan job** | Detect abandoned non-terminal jobs; resume if eligible, else fail/cancel explicitly with cleanup |
| **Orphan checkpoint** | Bind to job recovery; reclaim if job terminal or non-eligible |
| **Orphan intermediate artifacts** | Reclaim unpublished material so it never becomes searchable and does not leak capacity |
| **Abandoned processing after worker failure** | Platform recovery owns detection; outcome is resume, explicit terminal failure, or operator disposition—never silent abandon |

Orphan recovery MUST preserve exactly-once publish and active-version consistency.

## Progress Guarantees *(mandatory for this feature)*

| Condition | Operator meaning | Architectural response |
| --------- | ---------------- | ---------------------- |
| **Actively progressing** | Stage progress advancing within expectations | Continue; progress visible |
| **Waiting** | Blocked on back-pressure or dependency health | Visible wait reason; not treated as stall |
| **Stalled (no-progress)** | No meaningful progress beyond no-progress policy | Detect; escalate toward timeout / control action |
| **Timed out** | Escalation completed | `Timed Out` + reclamation |

Operators MUST be able to distinguish slow-but-progressing large-document work from stuck work.

## Failure Handling *(mandatory for this feature)*

| Class | Examples | Behavior |
| ----- | -------- | -------- |
| **Admission / capacity** | Backlog full, concurrency exhausted, workload class saturated | Delay under policy or reject with back-pressure; do not start expensive work |
| **Security / policy** | Unauthorized, wrong tenant, policy violation | Fail fast → `Failed`; no automatic retry |
| **Validation (permanent)** | Oversize, disallowed type, empty content after parse | Fail fast → `Failed`; no automatic retry loop |
| **Parse degraded** | Partial structure, recoverable text | Continue only if minimum-content gate passes; may end `Completed With Warnings` |
| **Parse failed** | Unreadable, unsafe | Fail fast → `Failed` unless reclassified as transient infra |
| **Transient infra** | Temporary storage/dependency blip | Retry/resume under bounded policy; idempotent re-entry |
| **Dependency unavailable / circuit open** | Parser, OCR, embedding, storage, database, LLM unavailable | Fail fast or defer; no cascading hot-loop; respect component health |
| **Timeout / cancel** | Deadline exceeded, operator/shutdown cancel | `Timed Out` / `Cancelled` + cleanup; active version unchanged |
| **Poison** | Repeated permanent failures for same version | Quarantine; stop automatic capacity use; operator review |
| **Dead-letter** | Unrecoverable job | Retain metadata; operator inspect / recover / discard |
| **Integrity / publish** | Incomplete searchable output, metadata gaps, inconsistency | Block publish; `Failed` with explicit reason; active version unchanged |
| **Orphan / abandoned** | Worker loss leaving job/checkpoint/artifacts without owner | Recovery ownership resumes, reclaims, or fails explicitly |

### Failure ownership (diagnostic)

| Ownership | Typical origins | Operational implication |
| --------- | --------------- | ----------------------- |
| **User input** | Disallowed submission, unauthorized, policy violation | Correct input/auth; usually no platform incident |
| **Document quality** | Corrupt/unreadable content, empty after parse, failed quality gates | Content/fix issue; may poison if repeated |
| **External dependency** | Parser/OCR/embedding/storage/database/LLM unavailability | Dependency/circuit health; defer or fail fast |
| **Platform** | Internal inconsistency, capacity accounting error, orphan leak | Platform incident; requires recovery ownership |
| **Operator action** | Explicit cancel, maintenance mode drain | Expected control action; cleanup required |

## Dependency Isolation & Health *(mandatory for this feature)*

| Dependency class | Isolation intent |
| ---------------- | ---------------- |
| Parser | Unavailability does not crash workers or unbounded-retry the platform |
| OCR | Optional path degrades or fails explicitly; does not block unrelated jobs forever |
| Embedding | Circuit and back-pressure contain outages |
| Storage | Admission/stage flow control; no silent data loss |
| Database | Fail fast / defer; no contradictory active versions |
| LLM / generation (if used in ingest) | Contained; not on interactive request path |

Component health (`Healthy` / `Degraded` / `Unavailable`) for stages and dependencies drives admission and whether work proceeds, degrades, fails fast, or waits under bounded policy.

## Resource Isolation, Fairness & Capacity *(mandatory for this feature)*

- Workload classes (small documents, large documents, background maintenance, migration) have isolated capacity so one class cannot monopolize the platform.
- **Service protection**: background processing, maintenance, and migration MUST NOT consume capacity required for interactive ingestion.
- Fairness across tenants/projects and starvation prevention are first-class scheduling objectives.
- Admission considers available capacity; concurrency and consumption remain bounded for predictable throughput.
- **Admission guarantees**: `Accepted` implies processing eligibility and a bounded capacity claim until terminal reclamation—not an unbounded promise.
- **Resource reclamation**: after cancel, timeout, permanent failure, worker restart, or worker crash, reserved capacity and reclaimable intermediate artifacts are released; leaks are treated as platform failures.
- Stage flow control ensures slow downstream stages regulate upstream work.

## Operational Modes *(mandatory for this feature)*

| Mode | Expected behavior |
| ---- | ----------------- |
| **Normal** | Full admission within capacity; all stages process under standard health |
| **Degraded** | Partial dependency/stage impairment; continue with explicit degraded outcomes, fail-fast, or restricted features per health—never silent corruption |
| **Maintenance** | Planned control posture; new admission may be delayed/restricted; in-flight work drains, completes, or cancels per policy with cleanup |
| **Recovery** | Orphan detection, resume/reclaim, and consistency restoration take priority; admission may be tightened until recovery objectives are met |
| **Admission Restricted** | New work delayed or rejected with explicit capacity/mode signal; accepted in-flight work continues under limits |

Mode changes MUST be observable and recorded in operational history where they affect job outcomes.

## Stage Contracts *(mandatory for this feature)*

Each major stage (admission/validation, parsing, chunk preparation, enrichment, indexing, publishing) MUST define, architecturally:

| Contract element | Purpose |
| ---------------- | ------- |
| **Accepted input** | What prior-stage completion produces that this stage may consume |
| **Produced output** | What successful completion makes available to the next stage (still unpublished until Publishing) |
| **Failure contract** | How the stage fails (ownership, retry eligibility, cleanup obligations) |
| **Completion contract** | What “stage complete” means for lifecycle transition and checkpoint eligibility |

Stage contracts MUST NOT allow a stage to publish Active Version visibility except the Publishing stage under exactly-once rules.

## Auditability & Configuration Safety *(mandatory for this feature)*

- Job operational history is complete: lifecycle, validation, retries, failures, cancellations, poison/dead-letter events, orphan recovery, mode effects, and reasoning.
- **End-to-end traceability**: correlation identity reconstructs the path from admission through every stage to terminal outcome.
- Configuration affecting behavior is validated, version-aware, observable, and auditable; unsafe configuration cannot apply silently.
- Audit history MUST NOT contain secrets.

## Migration *(mandatory for this feature)*

1. **Baseline** — Capture current ingest success rate, p95 job duration for normal docs, failure opacity, large-doc incidents, and any known partial-publish or duplicate-active cases on a golden corpus.
2. **Shadow / parity (optional but preferred)** — Compare scalable-path outcomes to baseline on the golden corpus without switching user-visible active versions until gates pass.
3. **Canary** — Enable for a small project cohort; require gate pass on memory budget, idempotent retry/resume, atomic publish, parse classification accuracy, and no increase in silent empty successes.
4. **Progressive enablement** — Expand cohort; watch back-pressure, degraded-parse / completed-with-warnings rates, poison/dead-letter rates, and fairness signals.
5. **Default on** — Make scalable path the sole production ingest behavior for all projects.
6. **Rollback** — Cohort-level disable returns new jobs to prior controlled behavior; document in-flight job handling (complete, cancel, or drain).

### Compatibility

Migration MUST support:

- **Forward compatibility** — Newer control plane can understand older job records/checkpoints sufficiently to complete, fail, or safely cancel them.
- **Backward compatibility** — Older searchable active versions remain valid and readable during and after upgrade.
- **Rolling deployment compatibility** — Platform can run mixed versions temporarily without dual active versions or partial publish.
- **Mixed-version worker compatibility** — Workers at adjacent versions can coexist; jobs are not corrupted by handoff across versions.

Migration MUST preserve: existing supported formats, project isolation, and the Document Intelligence structural model contract already established for ingest (006/007 lineage). Semantic changes are limited to reliability classification, lifecycle explicitness, publishing atomicity, and scalability/operability behavior.

## Recovery Objectives *(mandatory for this feature)*

- After processing capacity restart: resume-eligible jobs continue from checkpoint; others reach explicit terminal states; no partial active versions; orphans are detected and owned.
- After dependency outage: circuits open, admission adjusts, jobs fail fast/defer/timeout per policy; when health returns, normal processing resumes without manual platform rebuild.
- Service continuity: admission can still accept, delay, or reject with explicit signals while subsets of stages are Degraded/Unavailable or the platform is in a non-Normal operational mode.
- Resource reclamation: restart/crash paths reclaim reserved capacity and intermediate artifacts; no indefinite leaks.
- Resilience expectation: infrastructure failure results in controlled degradation and recoverable job outcomes, not silent corruption or duplicate publish.

## Testing *(mandatory for this feature)*

Production-confidence strategy (outcomes, not tools):

| Area | Intent |
| ---- | ------ |
| **Unit-level behavior** | Parse classification; gate pass/fail; retry eligibility; resume eligibility; idempotency of identity+version; exactly-once publish completion; back-pressure decision boundaries; poison thresholds; health-driven fail-fast; failure ownership; stage contract boundaries |
| **Integration** | Full lifecycle transitions; atomic/exactly-once publish under replacement; cancellation cleanup; security gates before expensive work; consistency of fully committed version |
| **Large document** | Bounded memory; checkpoint/resume; progress vs stall observability |
| **Large corpus** | Multi-document outcomes; fairness across projects |
| **Stress** | Burst above capacity; explicit admission behavior |
| **Soak** | Sustained concurrency-limit load; stable admission; no collapse |
| **Endurance** | Long-running operation with mixed workload classes; no progressive leak of capacity or inconsistency |
| **Chaos** | Dependency Unavailable injection; circuit open/close; no cascade |
| **Crash recovery** | Kill processing mid-stage; resume or explicit fail; orphan reclaim; active version consistent; no duplicate publish |
| **Restart** | Controlled restart; resume-eligible continue; capacity and artifacts reclaimed |
| **Orphan recovery** | Abandoned job/checkpoint/artifacts detected and owned to a defined outcome |
| **Progress / stall** | Slow progress vs no-progress escalation to timeout |
| **Service protection** | Background/maintenance/migration peak does not breach interactive ingestion capacity |
| **Operational modes** | Behavior under Normal / Degraded / Maintenance / Recovery / Admission Restricted matches contracts |
| **Exactly-once publish** | Retry after successful activation does not publish again; completion deterministic |
| **Retry exhaustion** | Permanent failures stop; poison/quarantine path |
| **Duplicate submission** | Same version does not create duplicate active content |
| **Back-pressure** | Admission and stage flow control under slow downstream |
| **Resource limits** | Hard caps enforced with explicit failure |
| **Degraded parsing matrix** | Success / degraded→warnings / failed fixtures |
| **Golden corpus regression** | Expected terminal classes and active-version integrity |
| **Rolling deployment** | Mixed-version workers; no partial publish |
| **Migration & rollback** | Canary enable, gate fail → rollback, progressive expand |

## Rollout *(mandatory for this feature)*

| Phase | Goal | Exit criteria |
| ----- | ---- | ------------- |
| **R0 – Instrumentation** | Observability, health, audit history live | Operators can query lifecycle, gates, retries, back-pressure, dependency health, progress/stall, mode |
| **R1 – Gates dark** | Validation/integrity/security gates compute (block in non-prod as needed) | False-positive rate understood on golden corpus |
| **R2 – Canary** | Scalable path on limited projects | Memory budget held; atomic/exactly-once publish proven; resume/cancel/orphan reclaim safe; no silent empty success |
| **R3 – Progressive** | Expand cohorts | Failure/warning/poison rates within bands; fairness and interactive protection hold; overload rejects correctly |
| **R4 – Default** | All projects on scalable path | Rollback drill tested; mixed-version compatibility validated; baseline metrics met or improved |

### Rollout governance

| Gate type | Intent |
| --------- | ------ |
| **Promotion criteria** | Evidence required to expand cohort (success/warning rates, zero partial publish, reclaim/orphan health, interactive protection) |
| **Rollback criteria** | Conditions that mandate cohort rollback (duplicate active versions, partial publish, resource leaks, interactive starvation, integrity regression) |
| **Rollout success gates** | Measurable checks that must pass before declaring a phase successful |
| **Phase exit criteria** | Explicit done-state for R0–R4; no silent “assumed good” expansion |

Progressive rollout remains measurable and reversible at every phase.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Documents up to the configured large-document profile complete (terminal success/warnings or explicit failure) without exceeding the declared large-document resource budget in soak tests.
- **SC-002**: Under intentional overload, at least 99% of excess submissions receive an explicit back-pressure/capacity response within the interactive submission time budget (no silent accept-into-unbounded-queue).
- **SC-003**: Zero jobs in the golden corpus reach `Completed` or `Completed With Warnings` when they produce no safe searchable content for the new version.
- **SC-004**: 100% of parse outcomes in the golden corpus are classified as success, degraded, or failed with a reason code.
- **SC-005**: After forced transient failure and resume/retry, duplicate **active** searchable units for the same logical document version equal zero.
- **SC-006**: Permanent validation/security failures do not enter unbounded automatic retry and surface a terminal explicit failure in 100% of fixture cases; poison path engages after repeated permanent failure policy threshold.
- **SC-007**: Operators can identify stage-level failure attribution for at least 95% of failed jobs using only exposed job signals and operational history.
- **SC-008**: Canary rollout can be enabled and rolled back for a project cohort in under 15 minutes of operator procedure time without affecting unrelated answer/search capabilities.
- **SC-009**: p95 end-to-end ingest latency for normal-sized documents on the golden corpus does not regress more than 15% versus the pre-migration baseline (large-document profile measured separately within its published SLA band).
- **SC-010**: During a 1-hour soak at concurrency limit, service remains available for admission decisions (accept/delay/reject) with no process-level collapse events.
- **SC-011**: During replacement ingest, 100% of search observations in the test harness see either the previous active version or the fully published new version—never a partial mix.
- **SC-012**: After mid-job cancellation or timeout, 100% of cases leave zero partial new-version content searchable and release reserved capacity.
- **SC-013**: After processing capacity crash/restart in the recovery suite, 100% of resume-eligible jobs either resume to a valid terminal success/warnings state or reach an explicit terminal failure—without duplicate active versions.
- **SC-014**: With one large-document workload at its class limit, small-document jobs from other projects still complete within their class SLA band (no indefinite starvation) in the fairness suite.
- **SC-015**: When a required dependency is forced Unavailable, dependent new work fails fast or defers under policy within the interactive/admission budget; unrelated workload classes continue within isolation budgets.
- **SC-016**: 100% of jobs in the operational audit suite retain lifecycle, validation, retry, and failure history sufficient for operator disposition without log archaeology.
- **SC-017**: Rolling/mixed-version deployment test completes with zero partial-publish events and zero dual-active versions for the same logical document identity.
- **SC-018**: In the exactly-once publish suite, forced retry/duplicate completion after a successful activation yields exactly one publish completion per Logical Document Version (zero additional activations).
- **SC-019**: In the orphan-recovery suite, 100% of injected orphan jobs, checkpoints, and intermediate artifacts reach a defined recovery outcome (resume, reclaim, explicit fail, or operator disposition) with zero indefinite capacity leaks.
- **SC-020**: In the progress suite, stalled (no-progress) jobs are detectable as distinct from actively progressing and waiting jobs, and escalate to timeout (or equivalent terminal control) in 100% of stall fixtures.
- **SC-021**: Under peak background/maintenance/migration load in the protection suite, interactive ingestion continues to admit or explicitly delay/reject within interactive capacity—never silent starvation of interactive work by background classes.
- **SC-022**: For fully committed versions in the consistency suite, ingestion terminal success/warnings, active published version, searchable observation, and metadata completeness agree in 100% of cases; no half-committed searchable state remains after restart.
- **SC-023**: Using only correlation identity, operators reconstruct admission-through-terminal stage history for at least 95% of jobs in the end-to-end observability suite.
- **SC-024**: Rollout governance drill: each progressive expansion records promotion evidence; injecting a rollback-criterion defect triggers cohort rollback successfully within the SC-008 operator time band.

## Assumptions

- Scope is the **document ingestion and indexing path** (admission through atomic publish-to-active). Answer generation and retrieval ranking algorithms are out of scope except where active-version publish quality affects them.
- “Large document” means above a configured threshold still within a hard maximum; exact thresholds are configuration/policy choices deferred to planning.
- Degraded parsing is allowed only when minimum usable content remains; otherwise fail-fast. Successful publish under degraded parsing uses `Completed With Warnings`.
- A single production ingest owner remains; this feature hardens that path (016-compatible).
- Existing Document Intelligence structural model and chunking ownership (006/007 lineage, subject to 016 sole-owner decisions) remain the semantic foundation.
- Interactive clients tolerate async job semantics (immediate job identity + later terminal state).
- Multi-tenant project isolation continues; fairness and budgets apply across projects and workload classes.
- Exact numeric defaults for batch size, concurrency, poison thresholds, and memory budgets are set during planning from measured baselines; success criteria bind to configured budgets and relative bands.
- “Graceful shutdown cancellation” may complete in-flight publish already inside the atomic publish step if stopping would be less safe than finishing the atomic switch; otherwise it cancels with cleanup—planning may refine the cut-line, but searchable atomicity MUST hold either way.
- Dead-letter and quarantine are operator-facing operational destinations conceptually; retention duration is an operational policy set at planning time.
- LLM dependency isolation applies only if ingest uses generation capabilities; if unused, the health/circuit requirement is vacuously satisfied for that dependency class.
