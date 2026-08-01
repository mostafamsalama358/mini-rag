# ADR-021-001 — Domain Skills as Domain Pack Capability

**Status**: Accepted  
**Date**: 2026-07-26  
**Feature**: 021-domain-skill-framework

---

## Context

RAG domains today rely on intent patterns and semantic parser field prediction to route retrieval. That creates non-determinism, dual maintenance (intents + fields + prompts), and broad unconstrained retrieval. The product requires explicit Skill selection (UI buttons) with Skills owning retrieval capability via Metadata Profiles.

Feature 016 M0 forbids new parallel production paths and new sole owners without a superseding ADR.

---

## Decision

1. **Domain Skills are a Capability**, not a Service, not a dedicated API resource replacing `/answer`, and not a new sole owner.
2. Skills and Metadata Profiles (implementation: `SkillFilterProfile`) are **Domain Pack extension points** under Field Registry (002).
3. Execution remains on the **sole Answer + Retrieval path**; Skill resolution configures that path.
4. Client-selected `skill_id` is the **only** skill router; no server-side skill/intent/alias classification for selection.
5. A dedicated Skill owner or parallel Skill pipeline requires a **superseding exception ADR** under 016 — not implied by this feature.

---

## Consequences

### Allowed

- Pack YAML `skills/` + `profiles/`
- Additive `skill_id` on answer requests
- UI Skill buttons
- Entity-only parse under Skill
- Profile-driven metadata filters on existing retriever
- Trace attributes for skill/profile ids
- Mapping 020 recommend-mode to explicit Skills

### Forbidden

- `SkillService` / Skill microservice as production owner
- Parallel skill-answer pipeline dual-running with sole path
- Server auto-selection or fuzzy remap of Skills
- Embedding filter lists inside Skill definitions
- Breaking frozen `/answer` **response** fields (015)

---

## References

- [spec.md](../spec.md)
- [plan.md](../plan.md)
- `specs/016-architecture-consolidation/governance/m0-freeze.md`
- `specs/020-pharmacy-recommendation/governance/adr-020-001-recommendation-as-capability.md`
