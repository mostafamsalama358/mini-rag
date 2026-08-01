# Quickstart: Unified Skill Runtime (Architecture Validation)

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

Validation drills for the plan/contracts—not a coding sprint. Implementation belongs to `/speckit-tasks` and implement.

---

## Prerequisites

- Read [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md)
- Skim [contracts/](./contracts/)
- Read [ADR-022-001](./governance/adr-022-001-skills-as-unified-runtime-configuration.md)
- Related: `specs/015-…`, `specs/016-…`, `specs/021-…`

---

## 1. Single Runtime Drill (FR-001, SC-001, A9)

**Steps**:

1. Locate Skill-enabled pack routing in `services/rag/pipeline/router.py` (or successor).
2. Confirm there is **no** “if pack has skills → legacy_executor” force path at completion design.
3. Trace Request → Skill Resolver → Pipeline Orchestrator → stages.

**Expected**: Skills configure unified runtime only (ADR-022-001).

---

## 2. Context Contract Drill (FR-003–FR-006, A3)

**Steps**:

1. Inspect `SkillExecutionContext` fields in design ([data-model.md](./data-model.md)).
2. Confirm `plan_field` / `plan_operation` are removed from Skill runtime contract.
3. Confirm Skill retrieval consumes context filters + strategy—not QueryPlan.field.

**Expected**: Sole immutable execution contract for Skills.

---

## 3. Strategy Registry Drill (FR-020, SC-003, SC-011)

**Steps**:

1. Walk StrategyRegistry → execute() path ([contracts/strategy-registry.md](./contracts/strategy-registry.md)).
2. For each mandatory strategy key, note distinct behavior claim.
3. Search shared runtime design for forbidden `if strategy ==` control flow.

**Expected**: True plugins; registration-only extension.

---

## 4. PipelineBuilder Drill (FR-022, SC-010, A5)

**Steps**:

1. Confirm declarative register → build → execute model.
2. Describe adding a no-op stage via registration only.
3. Confirm orchestrator core is not edited for that addition.

**Expected**: Workflow-ready composition.

---

## 5. God-Object Drill (FR-024, A7)

**Steps**:

1. List responsibilities today in `answer_service.answer_question`.
2. Map each to Skill Resolver / Orchestrator / stage executors in target design.
3. Confirm completion gate: answer_service is not Skill orchestration owner.

**Expected**: Distributed stage ownership.

---

## 6. Architecture Tests Drill (FR-023, SC-009)

**Steps**:

1. Review fail-closed table in [contracts/architecture-tests.md](./contracts/architecture-tests.md).
2. Plan `tests/architecture/test_022_*.py` coverage for each row.

**Expected**: Rules enforceable, not documentation-only.

---

## 7. Compatibility Drill (FR-013, SC-006)

**Steps**:

1. Confirm additive `skill_id` + UI buttons unchanged.
2. Confirm frozen `/answer` response fields unchanged.
3. Confirm existing Skill IDs remain.

**Expected**: Internal migration only.

---

## Suggested commands (post-implement)

```powershell
$env:PYTHONPATH = "D:\mini-rag\src"
python -m pytest tests/architecture -k "022 or 021" -q
python -m pytest tests/unit/services/rag/skills tests/integration -k "skill or 022" -q
```

Record outcomes in migration notes / audit report during implement—not required to run during `/speckit-plan`.

---

## Next

`/speckit-tasks` → implement → post-implementation architecture audit (spec validation section).
