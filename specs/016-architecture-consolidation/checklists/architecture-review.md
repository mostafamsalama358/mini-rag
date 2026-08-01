# Architecture Review Checklist

**Feature**: 016-architecture-consolidation  
**Use**: Required for new/changed production capabilities (see [`../contracts/governance.md`](../contracts/governance.md)).

## MUST (Governance)

- [ ] Single Owner identified per new/changed production concern (`governance/ownership-registry.md`)
- [ ] Canonical ContractRoles reused for shared concepts (`governance/contract-role-catalog.md`); new concept has ADR if reuse impossible
- [ ] Dependency direction respected (`contracts/dependency-boundaries.md`)
- [ ] No duplicate ownership (P1 / I7)
- [ ] No parallel production path (P2 / P4 / AP1)
- [ ] Lifecycle state declared for non-production / transitional pieces (`governance/lifecycle-registry.md`)
- [ ] ADR updated when architectural tradeoff changes
- [ ] Lifecycle/ownership docs updated when owner changes
- [ ] Architecture Validation considered before claiming production readiness

## MUST NOT (Forbidden Patterns AP1–AP14)

- [ ] AP1 Parallel production implementations
- [ ] AP2 Duplicate canonical contracts for one concept
- [ ] AP3 Multiple owners for the same concern
- [ ] AP4 Business orchestration inside infrastructure
- [ ] AP5 Domain logic inside Composition
- [ ] AP6 Core depending on concrete infrastructure
- [ ] AP7 Pipeline bypasses that skip owned concerns while claiming the capability
- [ ] AP8 Feature flags as permanent architecture
- [ ] AP9 Temporary migration code becoming permanent
- [ ] AP10 Hidden production paths
- [ ] AP11 Duplicate lifecycle ownership
- [ ] AP12 Owner chosen by age, folder, or historical package name
- [ ] AP13 Treating inactive capabilities as production-complete in docs
- [ ] AP14 Prescribing implementation layout as architecture

## Exception path

If any MUST/MUST NOT is waived: attach ADR using [`../governance/exception-adr-template.md`](../governance/exception-adr-template.md) with scope, duration, and exit criteria.

## Principles / Invariants quick refs

See [`../spec.md`](../spec.md) Architecture Principles (P1–P14) and Architecture Invariants (I1–I14).
