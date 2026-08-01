# Contract: SkillExecutionContext

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

---

## Normative rules

1. `SkillExecutionContext` is the **sole** Skill execution contract for Skill-bound stages.
2. Context is **immutable**. Enrichment uses derived context or StageResult only.
3. Shared mutable execution state is forbidden.
4. Skill-bound retrieval/generation/validation MUST NOT require `QueryPlan.field`, `QueryPlan.operation`, `plan_field`, or `plan_operation`.
5. Minimum carried attributes: SkillDefinition, SkillFilterProfile, metadata filters, parsed entities, validation, retrieval strategy, prompt binding, optional response schema, optional citation policy (see [data-model.md](../data-model.md)).

---

## Non-Skill traffic

Domains without Skills may continue to use full semantic QueryPlan on the unified pipeline. That path MUST NOT reintroduce a Skill QueryPlan bridge.

---

## Acceptance

- Architecture tests fail if bridge fields are required for Skill retrieval.
- Architecture tests fail if stages mutate SkillExecutionContext in place.
