# Architecture Audit — Unified Skill Runtime (022)

**Date**: 2026-07-28  
**Method**: Direct code inspection of runtime paths (not documentation-only)  
**Verdict**: **PARTIAL** — Skill path is first-class modular runtime; non-Skill path and full “one pipeline” goal remain incomplete.

---

## Executive summary

Feature 022 successfully cut over Skill-bound traffic to `SkillRuntimeOrchestrator` with declarative `PipelineBuilder` stages, removed inline Skill orchestration from `answer_service`, and eliminated router legacy-force for Skill profiles. Architecture gates (`test_022_*`) pass. The platform still runs **two execution graphs**: Skill stages via `SkillRuntimeOrchestrator`, and non-Skill traffic via inline `answer_service` (~900 lines) plus legacy/unified SpecKit orchestrator — so SC-012 item “Single Unified Runtime” is **PARTIAL**, not PASS.

---

## SC-012 / A9 checklist

| # | Gate | Score | Evidence |
|---|------|-------|----------|
| 1 | Single Unified Runtime | **PARTIAL** | Skill: `SkillRuntimeOrchestrator` + `PipelineBuilder`. Non-Skill: `answer_service.answer_question` inline chain OR `PipelineRouter` → legacy/unified SpecKit (`unified_orchestrator.py`, 633 lines). Not one stage graph for all traffic. |
| 2 | Legacy Skill executor removed | **PASS** | `router.py` uses `profile_has_skills` → `_skill_runtime.execute`; no `if getattr(profile, "skills")` legacy force. |
| 3 | QueryPlan bridge removed | **PARTIAL** | `plan_field`/`plan_operation` removed from schemas. `SkillExecutionContext.build_query_plan()` still derives QueryPlan for retrieval-stage compatibility; Skill stages prefer context filters. |
| 4 | SkillExecutionContext sole Skill contract | **PASS** | Skill stages receive immutable `skill_ctx`; orchestrator derives via `with_entities`. |
| 5 | Retrieval strategies are true plugins | **PASS** | Five strategies under `skills/strategies/`; registry `get` → `retrieve`; no strategy-name equality in `answer_service`. |
| 6 | Pipeline stages declaratively registered | **PARTIAL** | Skill chain registered in `SkillRuntimeOrchestrator._build_stages()`. Non-Skill/unified SpecKit graph is separate registration surface. |
| 7 | Shared runtime domain-independent | **PASS** | No static `from fields.pharmacy` under `src/services/rag/`; `test_022_no_pharmacy_imports.py`, `test_022_no_domain_field_branch.py` green. |
| 8 | answer_service no longer God object | **PARTIAL** | Skill orchestration removed (delegate + fail-closed). Non-Skill path still owns parse → retrieve → rerank → enrich → generate inline (~650 lines in `answer_question`). |
| 9 | Architecture tests enforce major rules | **PASS** | 8 `test_022_*` files + 021 gates; 21 passed in architecture `-k "022 or 021"` run. |
| 10 | Public API backward compatible | **PASS** | Additive `skill_id`, `set_skill_runtime`, frozen response via `FormattingStage` / `ResponseAdapter`; 021 contract tests pass. |

**Overall SC-012**: 6 PASS, 4 PARTIAL, 0 FAIL → **Feature not fully complete** per normative gate, but Skill cutover debt cleared.

---

## Design principle scores

| Principle | Score | Notes |
|-----------|-------|-------|
| One pipeline | **PARTIAL** | Skill and non-Skill do not share one orchestrator graph. |
| Context is the contract | **PASS** | Skill stages use `SkillExecutionContext`; no plan_field bridge on profiles. |
| No legacy Skill bypass | **PASS** | Router + answer_service delegate only. |
| Strategies are plugins | **PASS** | Registry pattern; distinct strategy modules present. |
| Domain packs own knowledge | **PASS** | Dynamic `domain_helpers`; interaction fetch injected as port. |
| Modular executors | **PARTIAL** | Skill side modular; `answer_service` still monolithic for generic domains. |
| Workflow-ready | **PARTIAL** | `PipelineBuilder` demonstrated for Skills; open-closed stage registration test not yet added (T043). |
| Compatibility first | **PASS** | 021 regression suite green alongside 022 gates. |

---

## Code-path findings

### Skill path (PASS)

```
/answer → PipelineRouter.profile_has_skills
       → SkillRuntimeOrchestrator.execute
       → PipelineBuilder stages: EntityParse → Validation → Retrieval → Generation → Formatting
```

- `composition.py` wires orchestrator and `rag_service.set_skill_runtime`.
- `answer_service` early-delegates or raises if runtime missing.

### Non-Skill path (PARTIAL)

```
/answer → PipelineRouter (mode legacy/unified/shadow)
       → LegacyPipelineExecutor OR UnifiedOrchestrator (SpecKit)
       OR direct RAGService.answer_question (legacy API path)
```

- `answer_service.answer_question` still coordinates full non-Skill pipeline inline.
- Uses `get_retrieval_strategy("default")` — registry compliant, but not stage-modular.

### Debt / risks

1. **Dual orchestrators** — Operators must reason about Skill vs SpecKit graphs until non-Skill migrates to shared stage library.
2. **`build_query_plan` bridge** — Still on `SkillExecutionContext` for retrieval payload shaping; document as transitional.
3. **Missing unit coverage** — No `test_pipeline_builder.py`, `test_strategy_registry.py`, per-stage contract suites (T009–T011, T042).
4. **`answer_service` size** — 904 lines; acceptable as legacy facade only if non-Skill migration is planned.

---

## FR-023 architecture test coverage

| Rule | Test | Status |
|------|------|--------|
| No pharmacy static imports | `test_022_no_pharmacy_imports.py` | PASS |
| No legacy Skill bypass | `test_022_no_legacy_skill_bypass.py` | PASS |
| No QueryPlan bridge fields | `test_022_no_queryplan_bridge.py` | PASS |
| No strategy-name branching | `test_022_no_strategy_name_branch.py` | PASS |
| No domain-field branching | `test_022_no_domain_field_branch.py` | PASS |
| Context immutability | `test_022_context_immutability.py` | PASS |
| No answer_service Skill orchestration | `test_022_no_answer_service_god_object.py` | PASS |
| Skill unified contract | `test_022_skill_unified_answer_contract.py` | PASS |

---

## Answer to SC-008

**Can Domain Skills be considered a fully first-class runtime architecture?**

**PARTIAL YES for Skill-bound traffic** — modular stages, immutable context, registry strategies, enforceable gates.  
**NO for the whole platform** until non-Skill traffic shares the same orchestration model and `answer_service` shrinks to a thin DI facade.

---

## Recommended follow-ups

1. Migrate non-Skill `/answer` onto shared stage executors (reuse retrieval/generation stages with `skill_ctx=None`).
2. Add T009–T011, T042–T043 unit tests to lock registration and stage contracts.
3. Retire or narrow `build_query_plan()` once retrieval stage is fully context-native.
4. Add `test_022_missing_skill.py` or formally alias 021 integration test in 022 docs.
