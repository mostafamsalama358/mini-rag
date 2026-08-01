# Data Model: Unified Skill Runtime

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Logical entities for the Skill runtime refactor. Pack YAML schemas from 021 remain the configuration SoT; 022 changes **runtime contracts**, not Skill ID vocabulary.

---

## 1. SkillExecutionContext (immutable)

Sole Skill execution contract passed through Skill workflow stages.

| Field | Type | Notes |
|-------|------|-------|
| skill | SkillDefinition | Pack-owned definition (no field/operation) |
| profile | SkillFilterProfile | Metadata Profile (filters + strategy) |
| metadata_filters | mapping | Effective filters from profile |
| entities | tuple[str, …] | Parsed entities |
| slots | mapping | Optional age/weight/gender/dose/disease |
| need_text | str \| null | Recommend Skills only |
| validation | SkillValidationRules | From Skill |
| retrieval_strategy | strategy key | From profile (Skill.retrieval may override key only) |
| prompt_ref | str | Skill.prompt or skill id |
| response_schema | mapping \| str \| null | Optional; additive |
| citation_policy | enum \| null | `strict` \| `relaxed` \| `leaflet_only` |
| domain_key | str | Active pack |
| skill_id | str | Selected Skill |
| recommend_mode | bool | From Skill.capabilities |

**Removed for Skill execution (022)**:

- `plan_field`
- `plan_operation`
- Any requirement that consumers read `QueryPlan.field` / `QueryPlan.operation` for Skill routing/retrieval

**Mutation rule**: frozen/immutable. Enrichment only via derived context (`replace`) or separate StageResult. Mutating in place is forbidden (architecture test).

---

## 2. SkillFilterProfile (pack config; evolved)

| Field | Type | Notes |
|-------|------|-------|
| id | str | Profile id referenced by Skill.profile |
| filters | SkillFilterProfileFilters | field/source/extra lists |
| retrieval_strategy | strategy key | SoT for strategy selection |
| fallback | mapping \| null | Controlled empty-result policy |
| notes | str \| null | Documentation |

**Removed**: `plan_field`, `plan_operation` (022 bridge elimination).

---

## 3. StageContract

| Field | Meaning |
|-------|---------|
| name / id | Stable stage id for registration |
| input | Declared input types (context + prior stage results) |
| output | Declared StageResult type |
| failure_conditions | Clarification / abort / no-context / error classes |
| side_effects | Allowed I/O (LLM, DB, metrics); default none beyond logging |

---

## 4. StageResult (immutable)

Per-stage output. Must not embed mutable shared state.

Examples:

| Stage | Result payload (logical) |
|-------|--------------------------|
| Validation | ok / clarification message |
| EntityParse | entities, slots, need_text, canonical_query, latency |
| Retrieval | documents, retrieval_path, strategy_id, counts |
| Generation | answer text, needs_clarification, prompt_ref used |
| Formatting | external answer payload fields (frozen shape) |

---

## 5. PipelineRegistration

| Concept | Notes |
|---------|-------|
| PipelineBuilder | Registers ordered stages |
| Stage Registry | Maps stage id → StageExecutor |
| Skill workflow chain | Default registered order for Skill-bound requests |
| Non-Skill chain | Separate or overlapping registration without Skill context |

---

## 6. RetrievalStrategy Plugin

| Field | Notes |
|-------|-------|
| name | Registry key (`default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup`, …) |
| execute(ctx, ports…) | Returns documents + path label |
| ports | Injected search/fetch interfaces (domain-agnostic) |

Mandatory distinct behaviors (not aliases): see [contracts/strategy-registry.md](./contracts/strategy-registry.md).

---

## 7. StrategyRegistry

| Operation | Notes |
|-----------|-------|
| register(strategy) | Implementation + name |
| get(name) | Resolve plugin |
| execute via plugin | Engine must not switch on name |

---

## 8. Extension Points (logical catalogs)

Documented surfaces (registration only):

- **Workflow stages**: Validation, Clarification, Safety, Guardrails, Tool Invocation, Formatter, Citation Enforcement, …
- **Retrieval strategies**: mandatory five + optional `keyword_only`, `graph`, …
- **Response formatters**: `markdown`, `json`, `clinical`, `citation_only`, …

Shipping every catalog entry is not required for 022 completion except mandatory strategies.

---

## 9. External compatibility entities (unchanged)

| Entity | Notes |
|--------|-------|
| Answer request `skill_id` | Additive; required when pack Skill registry non-empty |
| Frozen answer response fields | 015 contract |
| Skill catalog for UI | id, name, description |
| SkillDefinition YAML | Still profile/prompt/validation/capabilities only |

---

## 10. Relationships

```text
Client skill_id
  → SkillDefinition (pack)
  → SkillFilterProfile (pack)
  → SkillExecutionContext (runtime, immutable)
  → PipelineBuilder stages (each → StageResult)
  → StrategyRegistry → RetrievalStrategy (from context.retrieval_strategy)
  → Frozen external Answer response
```

---

## 11. Validation rules (runtime)

- Unknown / missing skill_id on Skill-required domain → fail closed (021)
- Missing profile reference → fail closed
- Unknown strategy key → fail closed or explicit documented default with log (prefer fail closed for Skill packs)
- Empty retrieval → existing no-context / clarification outcomes
- No silent broaden of Skill filters (021)
