# Contract: Architecture Tests (Enforceable)

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

---

## Purpose

Architecture rules MUST be enforced by automated tests that **FAIL** on violation. Documentation-only rules are insufficient for feature completion (spec A6 / FR-023 / SC-009).

## Required fail-closed cases

| Rule | FAIL if |
|------|---------|
| Domain independence | Shared runtime statically imports `fields.pharmacy.*` |
| Single runtime | Legacy Skill executor is reachable for Skill-bound traffic |
| No QueryPlan bridge | Skill execution requires/returns plan_field/plan_operation or QueryPlan.field for retrieval routing |
| Strategy plugins | Engine branches on strategy names |
| Domain field control | Engine branches on hardcoded domain field names for Skill control flow |
| Open/Closed strategies | Adding a strategy requires modifying engine retrieval stage beyond registration |
| Immutability | Pipeline stages mutate `SkillExecutionContext` |

## Suggested locations

- `tests/architecture/test_022_*.py`
- Reuse/extend helpers in `tests/architecture/_repo.py` as needed

## Acceptance

- Suite green on compliant tree.
- Intentional negative fixtures or AST/static scans cover each row above.
