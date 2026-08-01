# Migration Notes — Unified Skill Runtime (022)

**Feature**: 022-unified-skill-runtime | **Status**: Cutover complete (Skill path)

---

## Cutover completed

### Router Skill path (T017)

| Item | Status |
|------|--------|
| `PipelineRouter` routes Skill-enabled profiles via `profile_has_skills` → `_skill_runtime.execute` | **Done** |
| Legacy force branch `if getattr(profile, "skills", None):` removed | **Done** |
| Missing skill runtime raises `RuntimeError` | **Done** |

### answer_service God-object removal (T048)

| Item | Status |
|------|--------|
| Early delegate to `SkillRuntimeOrchestrator.execute_as_legacy_tuple` when runtime wired | **Done** |
| Skill profiles without runtime → `RuntimeError("Skill runtime not configured")` | **Done** |
| Inline Skill-first branch (`resolve_skill`, `entity_parse_async`, skill retrieval/prompt) removed | **Done** |
| Non-skill path retains semantic parse → default strategy registry retrieval → generation | **Done** |

Architecture gate: `tests/architecture/test_022_no_answer_service_god_object.py`.

### QueryPlan bridge

| Item | Status |
|------|--------|
| `plan_field` / `plan_operation` removed from `SkillFilterProfile` / runtime schemas | **Done** |
| Skill stages consume `SkillExecutionContext` via `SkillRuntimeOrchestrator` | **Done** |
| `apply.py` bridge module | **Removed** |

### Strategy registry

| Item | Status |
|------|--------|
| Five mandatory strategies as plugins under `skills/strategies/` | **Done** |
| Non-skill `answer_service` uses `get_retrieval_strategy("default")` only | **Done** |
| Engine strategy-name equality branches in `answer_service` | **Removed** |

### Domain independence

| Item | Status |
|------|--------|
| No static `fields.pharmacy` imports under `src/services/rag/` | **Verified** |
| Architecture scan covers full `src/services/rag/` | **Done** (`test_022_no_pharmacy_imports.py`) |
| `interaction_retrieval.py` remains pharmacy-shaped helper; Skill retrieval stage injects via port | **Accepted** |

### Wiring

- `src/services/rag/composition.py` constructs `SkillRuntimeOrchestrator` and calls `rag_service.set_skill_runtime(skill_runtime)`.
- `PipelineRouter` receives the same orchestrator as `skill_runtime`.

---

## Pre-cutover inventory (historical)

### Skill → legacy force in `router.py`

| Location | Behavior | Cutover action |
| `src/services/rag/pipeline/router.py` L94–118 | When `profile.skills` is non-empty, **always** routes to `LegacyPipelineExecutor` | **Removed** — Skill traffic uses `SkillRuntimeOrchestrator` |
| Comment L94–96 | Documents temporary 021 deferral | **Deleted** |

### QueryPlan bridge remnants

| Location | Bridge artifact | Cutover action |
| `src/services/rag/skills/context.py` | `build_query_plan()` | Retained for non-stage diagnostics only; Skill stages use context filters |
| `src/services/rag/skills/apply.py` | Deprecated wrapper | **Deleted** |
| `src/fields/schemas.py` | ~~`plan_field` / `plan_operation`~~ | **Removed in 022 foundation** |

### God-object / orchestrator coupling

| Location | Concern | Status |
| `src/services/rag/answer_service.py` | Monolithic Skill + non-Skill orchestration | **Skill path extracted**; non-Skill path still inline (~600 lines) |
| `src/services/rag/pipeline/skill_orchestrator.py` | Skill stage chain owner | **Done** |
| `src/services/rag/pipeline/unified_orchestrator.py` | SpecKit graph for non-Skill unified mode | **Parallel** to Skill orchestrator (see architecture audit) |

---

## Foundation modules

- `src/services/rag/skills/stages/` — stage contracts, validation, entity parse, retrieval, generation, formatting
- `src/services/rag/pipeline/builder/pipeline_builder.py` — declarative stage registration
- `src/services/rag/skills/strategies/` — plugin package with distinct strategy implementations
- `src/services/rag/pipeline/skill_orchestrator.py` — Skill runtime orchestrator

---

## Post-cutover verification

1. `tests/architecture/test_022_*.py` — all green
2. Skill-bound `/answer` with `skill_id` runs `SkillRuntimeOrchestrator` only (router + answer_service delegate)
3. No `plan_field` / `plan_operation` on runtime schemas
4. New strategy = register plugin only (no engine edit)

---

## Remaining debt

- Non-Skill traffic still uses inline orchestration in `answer_service` or legacy/unified SpecKit orchestrator — not a single graph for all traffic.
- Dedicated unit tests for `PipelineBuilder`, `StrategyRegistry`, and per-stage contracts (tasks T009–T011, T042) not yet added.
- `test_022_missing_skill.py` integration test not created (021 `test_021_missing_skill.py` covers behavior).
