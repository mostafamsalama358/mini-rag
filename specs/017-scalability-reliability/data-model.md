# Data Model: Production Scalability & Reliability

**Feature**: `017-scalability-reliability` | **Date**: 2026-07-18  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Logical entities for ingest control plane, versioning, and operability. Persistence mapping is an implementation concern; field names here are conceptual.

---

## 1. Ingest Job

Trackable asynchronous work unit for one Logical Document Version.

| Field | Required | Notes |
| ----- | -------- | ----- |
| `job_id` | yes | Stable job identity returned at admission |
| `correlation_id` | yes | End-to-end trace identity (FR-058) |
| `project_id` / tenant | yes | Tenant boundary |
| `logical_document_id` | yes | Identity being ingested/replaced |
| `logical_document_version` | yes | Version under that identity |
| `lifecycle_state` | yes | See [job-lifecycle.md](./contracts/job-lifecycle.md) |
| `workload_class` | yes | small / large / maintenance / migration |
| `parse_outcome` | no | Set after parse: success / degraded / failed |
| `failure_class` | no | Transient / permanent / capacity / etc. |
| `failure_ownership` | no | user_input / document_quality / external_dependency / platform / operator_action |
| `failure_reason` | no | Reason code + human-readable summary |
| `progress` | yes | Stage + coarse progress + progress_kind (progressing / waiting / stalled) |
| `checkpoint_ref` | no | Latest restart-safe checkpoint |
| `publish_completion_id` | no | Set exactly once on successful activation |
| `configuration_version` | yes | Validated config snapshot in effect |
| `operational_mode_at_admit` | yes | Mode when accepted |
| `created_at` / `updated_at` | yes | Timestamps |
| `terminal_at` | no | Set when entering a terminal state |

**Validation**:
- Terminal states are irreversible for this `job_id`.
- `Completed` / `Completed With Warnings` require `publish_completion_id`.
- `Failed` / `Cancelled` / `Timed Out` MUST NOT set a new Active Version.

**State transitions**: Normative list in [job-lifecycle.md](./contracts/job-lifecycle.md).

---

## 2. Logical Document Identity

Stable document identity across replacements.

| Field | Required | Notes |
| ----- | -------- | ----- |
| `logical_document_id` | yes | Aligns with existing asset/document identity |
| `project_id` | yes | Tenant scope |
| `active_version` | no | Current Active Version id, if any |

**Validation**: At most one `active_version` per identity (FR-034).

---

## 3. Logical Document Version

Immutable content revision under an identity; idempotency unit with identity.

| Field | Required | Notes |
| ----- | -------- | ----- |
| `logical_document_id` | yes | Parent identity |
| `version_id` | yes | Immutable version key |
| `status` | yes | `preparing` / `active` / `superseded` / `abandoned` |
| `fully_committed` | yes | Consistency-model flag (FR-061) |
| `quality_warnings` | no | Present when completed with warnings |
| `superseded_by` | no | Set when a newer version becomes active |

**Validation**:
- Transition to `active` occurs only via exactly-once publish completion.
- `fully_committed` true only when job terminal success/warnings ∧ active ∧ searchable ∧ metadata complete.

---

## 4. Checkpoint

Restart-safe committed progress.

| Field | Required | Notes |
| ----- | -------- | ----- |
| `checkpoint_id` | yes | |
| `job_id` | yes | Owning job |
| `stage` | yes | Stage that committed |
| `progress_token` | yes | Opaque resume cursor (conceptual) |
| `created_at` | yes | |
| `reclaimable` | yes | Whether orphan recovery may delete |

**Validation**: Resume eligibility requires non-reclaimed checkpoint, non-terminal job, not poison/dead-lettered, dependency health allows, within retry/time policy (FR-032).

---

## 5. Publish Completion

Deterministic exactly-once activation record.

| Field | Required | Notes |
| ----- | -------- | ----- |
| `publish_completion_id` | yes | Unique |
| `logical_document_id` | yes | |
| `version_id` | yes | |
| `job_id` | yes | |
| `completed_at` | yes | |
| `previous_active_version` | no | Superseded version, if any |

**Validation**: Unique constraint on `(logical_document_id, version_id)` successful publish — second attempt is a no-op (FR-052).

---

## 6. Parse Outcome Record

| Field | Required | Notes |
| ----- | -------- | ----- |
| `job_id` | yes | |
| `classification` | yes | success / degraded / failed |
| `reason_code` | yes | |
| `minimum_content_gate` | yes | pass / fail |

---

## 7. Validation Gate Result

| Field | Required | Notes |
| ----- | -------- | ----- |
| `job_id` | yes | |
| `gate_name` | yes | security / admission / post_parse / integrity / … |
| `passed` | yes | |
| `reason` | no | Required if failed |
| `recorded_at` | yes | |

---

## 8. Operational History Event

Append-only audit event for a job.

| Field | Required | Notes |
| ----- | -------- | ----- |
| `job_id` | yes | |
| `correlation_id` | yes | |
| `event_type` | yes | lifecycle / validation / retry / failure / cancel / orphan / mode / progress |
| `stage` | no | |
| `detail` | yes | Structured, non-secret |
| `recorded_at` | yes | |

**Validation**: No secrets/PII dumps (NFR-006). Sufficient to reconstruct admission→terminal path (FR-058).

---

## 9. Poison / Dead-Letter Record

| Field | Required | Notes |
| ----- | -------- | ----- |
| `record_id` | yes | |
| `logical_document_id` | yes | |
| `version_id` | yes | |
| `kind` | yes | poison / dead_letter |
| `failure_history_ref` | yes | Link to retained failures |
| `disposition` | yes | quarantined / cleared_for_retry / discarded / terminal |
| `updated_at` | yes | |

---

## 10. Orphan Record

| Field | Required | Notes |
| ----- | -------- | ----- |
| `orphan_id` | yes | |
| `orphan_type` | yes | job / checkpoint / intermediate_artifact |
| `job_id` | no | If known |
| `recovery_ownership` | yes | platform_recovery / operator |
| `outcome` | no | resumed / reclaimed / failed_explicit / operator_pending |
| `detected_at` | yes | |

---

## 11. Resource Budget / Capacity Claim

| Field | Required | Notes |
| ----- | -------- | ----- |
| `claim_id` | yes | |
| `job_id` | yes | |
| `workload_class` | yes | |
| `reserved_units` | yes | Conceptual capacity units |
| `state` | yes | held / released |
| `released_at` | no | Required when released |

**Validation**: Terminal job, cancel, timeout, crash recovery MUST end in `released` (FR-056).

---

## 12. Component Health & Operational Mode

| Entity | Fields | Notes |
| ------ | ------ | ----- |
| **Component Health** | `component`, `state` (Healthy/Degraded/Unavailable), `updated_at` | Per major stage/dependency |
| **Operational Mode** | `mode`, `reason`, `updated_at` | Platform posture (FR-060) |

---

## Relationships

```text
LogicalDocumentIdentity 1──* LogicalDocumentVersion
LogicalDocumentIdentity 1──0..1 ActiveVersion (version)
LogicalDocumentVersion 1──* IngestJob (attempts; successful publish ≤ 1)
IngestJob 1──* Checkpoint
IngestJob 1──* OperationalHistoryEvent
IngestJob 1──* ValidationGateResult
IngestJob 0..1 PublishCompletion
IngestJob 1──0..1 CapacityClaim
LogicalDocumentVersion 0..1 Poison/DeadLetterRecord
```

---

## Consistency rules (summary)

1. Search observes Active Version only.
2. PublishCompletion creates/switches Active Version exactly once per version.
3. Failed/cancelled/timed-out jobs leave Active Version unchanged.
4. `fully_committed` iff consistency model predicates hold (spec FR-061).
5. Orphan recovery never activates a version without integrity + exactly-once publish.
