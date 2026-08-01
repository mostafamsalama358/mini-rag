# ADR-022-001 — Domain Skills as Unified Runtime Configuration

**Status**: Accepted  
**Date**: 2026-07-28  
**Feature**: 022-unified-skill-runtime

---

## Context

Feature 021 introduced Domain Skills, `SkillExecutionContext`, Metadata Profiles, prompt ownership, and retrieval strategy keys, but Skill-enabled traffic still depended on a legacy answer executor bypass. That left a dual-runtime model: Skills configured behavior while a separate legacy path still owned execution for Skill packs.

Feature 016 M0 forbids parallel production paths and new sole owners without a superseding ADR. Completing Skills as a first-class product capability requires a single execution model—not a Skill-owned pipeline.

---

## Decision

**Domain Skills are configuration for the Unified Runtime.** They do not own a separate execution pipeline.

1. Skill resolution produces an immutable `SkillExecutionContext` that configures the unified pipeline.
2. The unified pipeline is the only Skill execution pipeline.
3. Skills remain a Domain Pack capability on the sole Answer + Retrieval path (016 / ADR-021-001).
4. A dedicated Skill runtime, Skill-specific pipeline family, or revived legacy Skill executor requires a **superseding exception ADR**—not implied by this feature.

---

## Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| **Legacy Skill Executor** | Dual maintenance; Skills never become first-class; contradicts 015/016 sole-path intent. |
| **Separate Skill Runtime** | New parallel production path / ownership surface; violates M0 freeze without exceptional justification. |
| **Dual Runtime** (unified + legacy Skill path) | Permanent fork; higher test cost; divergent behavior under the same Skill IDs. |
| **Skill-specific Pipelines** | N pipelines for N Skill families; blocks reusable workflow stages and plugins. |

---

## Reasoning

- **Single execution model** — one place to reason about Skill and non-Skill traffic.
- **Single ownership** — Answer/Retrieval sole path remains; Skills configure, they do not own.
- **Lower maintenance cost** — no legacy bypass or duplicated stage logic.
- **Easier testing** — architecture gates and golden Skill scenarios target one pipeline.
- **Better plugin architecture** — strategies, stages, and formatters register into one runtime.
- **Future workflow stages become reusable** — validation, clarification, guardrails, tools, citation enforcement compose on the same chain.

---

## Consequences

### Allowed

- Skill → `SkillExecutionContext` → unified pipeline stage chain → frozen external response
- Declarative stage registration and retrieval strategy plugin registry
- Pack-owned Skills/profiles/prompts as configuration only
- Architecture tests that fail closed on dual-runtime / bridge / domain-coupling regressions

### Forbidden

- Skill → legacy executor as a supported production path
- Separate Skill Runtime or Skill-specific pipeline families
- Permanent dual runtime for Skill traffic
- Treating Skills as owners of orchestration (God-object answer service coordinating the entire Skill runtime)

---

## References

- [spec.md](../spec.md)
- [ADR-021-001](../../021-domain-skill-framework/governance/adr-021-001-skills-as-domain-pack-capability.md)
- `specs/016-architecture-consolidation/governance/m0-freeze.md`
- `specs/015-unified-pipeline-migration/`
