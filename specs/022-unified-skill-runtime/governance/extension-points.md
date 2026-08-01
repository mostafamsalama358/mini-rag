# Extension Points — Unified Skill Runtime (022)

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

Declarative registration surfaces. Consumers MUST NOT branch on names in engine code.

---

## Stage registration

| Surface | Module | API |
|---------|--------|-----|
| Stage contract | `src/services/rag/skills/stages/contracts.py` | `StageExecutor` Protocol, `StageResult`, `StageContract` |
| Pipeline composition | `src/services/rag/pipeline/builder/pipeline_builder.py` | `PipelineBuilder.register(stage).build()` |

Stages are registered in Skill/pack configuration and resolved at orchestrator startup — no per-Skill orchestrator edits.

---

## Strategy registration

| Surface | Module | API |
|---------|--------|-----|
| Strategy protocol | `src/services/rag/skills/strategies/base.py` | `RetrievalStrategy` |
| Registry | `src/services/rag/skills/strategies/registry.py` | `StrategyRegistry.register`, `.get`, `.execute` |
| Module helpers | `src/services/rag/skills/strategies/__init__.py` | `register_strategy`, `get_retrieval_strategy` |
| Profile binding | `fields/{domain}/profiles/*.yaml` | `retrieval_strategy` key on `SkillFilterProfile` |

Built-in strategies: `default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup`.

---

## Formatter / output registration

| Surface | Module | Notes |
|---------|--------|-------|
| Skill prompt | `fields/{domain}/skills/*.yaml` | `prompt` → `SkillExecutionContext.prompt_ref` |
| Response schema | `SkillDefinition.response_schema` | Optional additive contract |
| Citation policy | `SkillDefinition.citation_policy` | `strict` / `relaxed` / `leaflet_only` |

Formatter plugins (future): register via Domain Pack `output` block; unified pipeline stage consumes `SkillExecutionContext.response_schema`.

---

## Domain Pack surfaces (unchanged)

- Skill IDs and profile references — `fields/{domain}/skills/*.yaml`
- Metadata profiles — `fields/{domain}/profiles/*.yaml`
- API `skill_id` — frozen additive request field (015)

See also: `specs/022-unified-skill-runtime/contracts/extension-points.md` (when present).
