# Contract: Ownership and Unified Skill Runtime

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28  
**Authority**: [ADR-022-001](../governance/adr-022-001-skills-as-unified-runtime-configuration.md), ADR-021-001, Features 015 / 016

---

## Ownership (normative)

| Concern | Sole owner / concern | Forbidden |
|---------|----------------------|-----------|
| Skill & profile definitions | Domain Pack (Field Registry) | Engine hard-coded skill lists |
| Skill selection authority | Client (`skill_id`) | Server skill/intent routers |
| Skill execution pipeline | Unified Answer pipeline | Legacy Skill executor; separate Skill runtime; dual Skill path |
| Stage orchestration | Pipeline Orchestrator + PipelineBuilder | God-object answer_service owning all Skill stages inline |
| Retrieval strategy selection | SkillExecutionContext → StrategyRegistry | Engine `if strategy ==` / domain field switches |
| Frozen external answer response | 015 contract | Breaking response fields |
| Eval runners | 019 | Request-path evaluation owner |

**M0**: Skills configure the sole path; they do not create a new sole owner named “Skill Execution.”

---

## Canonical Skill flow

```text
Request (+ skill_id)
  → Skill Resolver
  → SkillExecutionContext (immutable)
  → Pipeline Orchestrator (registered stages)
  → Response (frozen external contract)
```

Forbidden:

```text
Request → Skill → Legacy Executor → Response
```

---

## Acceptance

- Architecture tests prove Skill packs do not force legacy executor.
- No production dual Skill runtime remains at feature completion.
