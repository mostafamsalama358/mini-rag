# Data Model: Architecture Consolidation (Governance Entities)

**Feature**: 016-architecture-consolidation | **Date**: 2026-07-18

This model describes **architectural governance entities**, not database tables or runtime DTOs. Physical type names and storage schemas are non-normative.

---

## Entity Overview

```text
Capability
  └── requires many Concern
        └── has exactly one OwnershipBinding (when production)
        └── exposes ContractRole(s)
        └── has LifecycleState

ArchitectureDecision
  └── authorized by Principle | Invariant | ADR

MigrationPhase
  └── has exit ValidationGate(s)

ValidationGate
  └── belongs to category: Architecture | Code | Runtime | Operational
```

---

## Capability

Logical production purpose.

| Field | Type | Rules |
|-------|------|-------|
| `id` | enum | `answer` \| `ingest` \| `search` \| `offline_evaluation` |
| `purpose` | text | Non-empty; stakeholder-readable |
| `required_concerns` | set\<ConcernRef\> | Non-empty for production capabilities |
| `required_contract_roles` | set\<ContractRole\> | One canonical role per shared concept used |
| `allowed_dependencies` | dependency rules | Must match layer vocabulary |
| `forbidden_dependencies` | dependency rules | Includes anti-pattern references |

**Validation**:
- Exactly one production execution path meaning per capability after its sole-owner phase (I1).
- No undocumented additional production path (I13).

---

## Concern

Single architectural responsibility.

| Field | Type | Rules |
|-------|------|-------|
| `id` | stable logical id | Not a folder path |
| `description` | text | What sole ownership means |
| `capability_refs` | set\<CapabilityId\> | Concerns may serve multiple capabilities (e.g. retrieval) |
| `production` | bool | Whether currently on a production path |

**Validation**:
- At most one Active Production Owner when `production=true` (I2/I7).

---

## OwnershipBinding

Binding of roles to a concern.

| Field | Type | Rules |
|-------|------|-------|
| `concern_id` | ConcernRef | Required |
| `owner` | Party | Exactly one |
| `contributors` | set\<Party\> | Optional; ≠ owner |
| `consumers` | set\<Party\> | Depend on published contracts only |
| `selection_rationale` | text | Must cite Owner Selection Criteria when contested |
| `selected_at_phase` | MigrationPhaseId \| null | Set when established during consolidation |

**Party** is a logical role (e.g. “Canonical Retrieval Owner”, “Composition”, “Domain Packs”), not a package path.

**State transitions**:
- Unbound → Active Production Owner (via selection criteria)
- Active → Consolidate Into Owner / Retire After Cutover (for competitors)
- Active → (owner transfer) only with governance update + criteria

---

## ContractRole

Canonical contract family for a shared concept.

| Field | Type | Rules |
|-------|------|-------|
| `role` | enum (extensible) | Examples: `understood_query`, `retrieval_plan_intent`, `retrieval_results`, `evidence_set`, `assembled_context`, `generated_answer`, `external_answer_response`, `parsed_document`, `indexable_units`, `persistence_ack`, `external_search_response` |
| `concept` | text | Human concept name |
| `owner_concern` | ConcernRef | Authority for contract evolution |
| `compatibility` | policy | Breaking changes require ADR or pack/version notes as applicable |

**Validation**:
- One production contract family per `concept` (P3).
- Duplicate production roles for the same concept forbidden after M3.

---

## LifecycleState

| Value | Meaning | Allowed production traffic |
|-------|---------|----------------------------|
| `active_production_owner` | Sole production implementation | Yes |
| `consolidate_into_owner` | Merging into owner | No (as independent owner) |
| `retire_after_cutover` | Pending retirement | No after cutover gate |
| `activation_pending_consumer` | Built/partial, awaiting consumer | No |
| `dormant_capability` | Intentionally unused | No |
| `research_capability` | Exploratory | No |
| `transitional_diagnostic` | Dual-run/compare | No as user-visible owner |

**Transitions** (allowed):

```text
research_capability → dormant_capability → activation_pending_consumer → active_production_owner
active_production_owner → (competitor) consolidate_into_owner | retire_after_cutover
transitional_diagnostic → retire_after_cutover
any non-active → archived (implementation docs) after M8 honesty gate
```

**Forbidden**: simultaneous `active_production_owner` for two parties on one concern (AP11/AP3).

---

## ArchitectureDecision

| Field | Type | Rules |
|-------|------|-------|
| `id` | `D#` or `ADR-#` | Stable |
| `statement` | text | Decision text |
| `authority` | `principle` \| `invariant` \| `adr` \| `compatibility` | Required |
| `adr_ref` | ADR id \| null | Required if authority=`adr` |

Standing philosophy MUST NOT be stored as ADR rows (research R-011).

---

## ADR Record

| Field | Type | Rules |
|-------|------|-------|
| `id` | ADR-001… | Contested tradeoff only |
| `context` | text | Real problem |
| `decision` | text | Selected option |
| `alternatives` | list | ≥2 valid alternatives |
| `tradeoffs` | text | Honest costs |

Current normative ADRs: 001–004 (see spec).

---

## MigrationPhase

| Field | Type | Rules |
|-------|------|-------|
| `id` | `M0`…`M8` | Ordered |
| `name` | text | Outcome-oriented |
| `outcome` | text | Observable end state |
| `exit_gates` | set\<ValidationGateRef\> | Non-empty |
| `predecessor` | phase \| null | Must complete first for retirement-related work |

**Rule**: Retirement gates MUST NOT open before sole-owner gates for the same concern (P11).

---

## ValidationGate

| Field | Type | Rules |
|-------|------|-------|
| `id` | `V-*` | Stable |
| `category` | `architecture` \| `code` \| `runtime` \| `operational` \| `process` | Required |
| `assertion` | text | Pass/fail observable |
| `phase` | MigrationPhaseId \| ongoing | When required |

---

## AntiPatternRef

| Field | Type | Rules |
|-------|------|-------|
| `id` | `AP1`… | From spec |
| `superseded_by_adr` | ADR id \| null | Required if temporarily allowed |
| `scope` | text | If superseded: bounded scope + duration + exit |

---

## Relationships

| From | To | Cardinality | Notes |
|------|----|-------------|-------|
| Capability | Concern | 1..* | Required concerns |
| Concern | OwnershipBinding | 0..1 active | Exactly 1 when production |
| Concern | ContractRole | 0..* | Published contracts |
| Concern | LifecycleState | 1 | Per implementation/competitor instance in migration docs |
| MigrationPhase | ValidationGate | 1..* | Exit criteria |
| ArchitectureDecision | ADR | 0..1 | If contested |

---

## What this model intentionally excludes

- ORM entities, tables, migrations
- Concrete Python class names
- Package/module inventories
- Provider-specific payloads
- Evaluation metric schemas (owned by Offline Evaluation capability elsewhere)
