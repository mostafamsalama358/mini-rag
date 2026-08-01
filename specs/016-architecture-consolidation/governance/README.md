# Architecture Consolidation Governance

**Feature**: 016-architecture-consolidation

This directory holds **governance registries and procedures**, not a component catalog of source packages.

## Purpose

- Publish logical ownership so architects resolve Owner / Contributors / Consumers without reading code
- Track lifecycle honesty for non-production capabilities
- Catalog canonical contract roles (concept identity, not type names)
- Provide migration gates, retirement checks, and review procedures

## How to find the owner

1. Open [`capability-cards.md`](./capability-cards.md) for the capability’s required concerns.
2. Look up each concern in [`ownership-registry.md`](./ownership-registry.md) — exactly one **Owner**.
3. Check [`lifecycle-registry.md`](./lifecycle-registry.md) if the concern may be non-production.
4. Use [`contract-role-catalog.md`](./contract-role-catalog.md) for shared contracts.
5. Only if still unclear: open an architecture review using [`../checklists/architecture-review.md`](../checklists/architecture-review.md).

**Do not** treat folder or package names as owner identity (Owner Selection Criteria / AP12).

## Normative sources

| Document | Role |
|----------|------|
| [`../spec.md`](../spec.md) | Principles, invariants, anti-patterns, ADRs |
| [`../plan.md`](../plan.md) | Planning summary |
| [`../contracts/`](../contracts/) | Enforceable contracts |
| [`../quickstart.md`](../quickstart.md) | Validation scenarios |

## Dual-path freeze (M0)

See [`m0-freeze.md`](./m0-freeze.md). No new parallel production implementations without a superseding ADR.
