# Contract: Lifecycle & Disposition

**Feature**: 016-architecture-consolidation | **Version**: 1.0.0

Normative lifecycle vocabulary and disposition rules for concerns and capabilities.

---

## Lifecycle States

| State | User-visible production owner? | Notes |
|-------|--------------------------------|-------|
| Active Production Owner | Yes (sole) | Exactly one per production concern |
| Consolidate Into Owner | No | Responsibility merges into owner |
| Retire After Cutover | No (after gate) | Removal/archive only after sole owner |
| Activation Pending Consumer | No | Awaiting declared consumer |
| Dormant Capability | No | Intentionally unused |
| Research Capability | No | Exploratory; not a dependency |
| Transitional Diagnostic | No | Dual-run/compare only |

---

## Disposition Rules

1. Competing production implementations → select one Active Production Owner via Owner Selection Criteria; others Consolidate or Retire After Cutover.
2. Duplicate contracts for one concept → one canonical ContractRole; retire others after consumer migration.
3. Dual-run/shadow → Transitional Diagnostic; never user-visible owner; Retire After Cutover after sole-path.
4. Built with no consumer → Activation Pending Consumer / Dormant / Research — never implied production-complete.
5. Domain rules in core → Consolidate Into Domain Pack ownership.
6. Labels like “deprecated” without traffic move → insufficient for retirement.

---

## Owner Selection (binding)

**Select by**: architectural alignment, production maturity, operational stability, validation results, extensibility, maintainability.

**Never by**: implementation age, historical ownership alone, folder/package names, convenience of caller graph alone, feature-flag presence.

Contested selections SHOULD produce an ADR when multiple alternatives were valid.

---

## Convergence Sequence

1. Name concern + required ContractRoles  
2. Select Active Production Owner  
3. Cut over consumers  
4. Validate (Architecture/Code/Runtime/Operational)  
5. Retire competitors + diagnostics  
6. Update lifecycle records; amend ADR if tradeoff changed  

---

## Honesty Rule

Public and agent-facing architecture documentation MUST match LifecycleState. Claiming production-complete status for Activation Pending / Dormant / Research capabilities is a contract violation.
