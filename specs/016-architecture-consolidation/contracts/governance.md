# Contract: Architecture Governance

**Feature**: 016-architecture-consolidation | **Version**: 1.0.0

Normative contract for how capabilities and concerns may evolve after consolidation. Supersession requires an ADR with scope, duration, and exit criteria.

---

## Purpose

Prevent architectural drift by making ownership, contracts, lifecycle, and dependency rules enforceable at review time.

---

## Rules for New or Changed Capabilities

A change that introduces or modifies a production capability MUST provide:

| Requirement | Evidence |
|-------------|----------|
| Single Owner per new/changed production concern | OwnershipBinding record (implementation docs OK) |
| Reuse of canonical ContractRoles for shared concepts | Mapping table or explicit “new concept” ADR |
| Dependency direction compliance | Layer check vs [dependency-boundaries.md](./dependency-boundaries.md) |
| No duplicate ownership | Review assertion |
| No parallel production path | Path selection / wiring assertion |
| Lifecycle honesty | LifecycleState for non-production pieces |
| ADR update when tradeoff changes | ADR diff |
| Lifecycle/ownership doc update when owner changes | Doc diff |

**Acceptance**: Architecture review MAY NOT approve production readiness if any row is missing without a superseding ADR.

---

## Rules for Retirement

| Requirement | Evidence |
|-------------|----------|
| Sole Active Production Owner exists | OwnershipBinding |
| Zero production consumers of retiree | Consumer scan / review |
| Rollback available until gate passes | Rollback note |
| Diagnostics cannot remain as hidden path | Lifecycle ≠ transitional in production wiring |

---

## Review Obligations

1. Reject Forbidden Patterns (spec AP1–AP14) unless superseded.
2. Exception ADRs MUST include: problem, alternatives, tradeoffs, scope, duration, exit criteria.
3. This contract is the governance source of truth; detailed inventories are not.

---

## Non-Goals

- Defining coding standards beyond dependency/ownership
- Mandating specific CI tools
- Ranking algorithms or quality metrics
