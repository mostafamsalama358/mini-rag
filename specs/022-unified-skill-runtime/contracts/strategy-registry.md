# Contract: Retrieval Strategy Registry

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

---

## Required resolution path

```text
SkillExecutionContext.retrieval_strategy
  → StrategyRegistry.get(name)
  → RetrievalStrategy.execute(context, ports…)
```

## Forbidden (shared runtime)

- `if strategy == "…"`
- `switch(strategy)` / equivalent name branching for control flow
- Selecting strategy by domain field names (`interactions`, `dosage`, …)

## Mandatory plugins (distinct behavior)

| Key | Distinct behavior (normative intent) |
|-----|--------------------------------------|
| `default` | Profile-filtered hybrid-capable default search composition used by Skill packs when unspecified |
| `semantic_only` | Dense/semantic path without sparse/hybrid fusion |
| `hybrid` | Dense + sparse (or equivalent) fusion when enabled |
| `document_lookup` | Document/entity-scoped document retrieval priority |
| `pair_lookup` | Structured pair/document fetch via pack port, then vector fallback |

Aliases that share identical behavior are **not** compliant.

## Extension rule

Adding a strategy requires:

1. Implementation  
2. Registration  

No shared-engine modification.

## Acceptance

- Architecture tests detect strategy-name branching in shared runtime.
- Unit tests prove distinct paths/labels or compositions per mandatory key.
- Negative test: unregistered strategy does not require editing retrieval stage code to “support” a new name beyond registration.
