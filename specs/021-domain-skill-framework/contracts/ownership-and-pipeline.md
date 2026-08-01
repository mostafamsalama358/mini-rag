# Contract: Ownership and Skill Pipeline

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26  
**Authority**: [ADR-021-001](../governance/adr-021-001-skills-as-domain-pack-capability.md), Features 016 / 002 / 004 / 009 / 010 / 013

---

## Ownership (normative)

| Concern | Sole owner / concern | Forbidden |
|---------|----------------------|-----------|
| Skill & Metadata Profile definitions | Domain Pack (Field Registry) | Engine hard-coded pharmacy skill lists |
| Skill selection authority | Client (`skill_id`) | Server intent/skill/alias/command router |
| Entity / slot extraction under Skill | Query Understanding | Predicting skill/field for routing |
| Profile filter application + hybrid/fusion/rerank | Retrieval (planner/engine) | Parallel skill retriever owner |
| Prompt template + output policy application | Answer Generation | Second answer composer path |
| Skill resolution orchestration | Existing Answer path application layer | New SkillService sole owner |
| Eval runners / skill-scoped gates | Feature 019 | Request-path evaluation owner |

**M0**: No parallel production skill path. Logical Skill pipeline ≠ new deployable orchestrator.

---

## Logical pipeline (normative concern order)

```text
User
  → Selected Skill (client)
  → Query Parser (entities/slots only)
  → Skill Registry resolve
  → Metadata Profile (SkillFilterProfile)
  → Retriever (profile filters + hybrid)
  → Reranker
  → Answer Generation (Skill prompt + output policy)
```

### Clarifications

1. Registry/profile resolution are Domain Pack load/lookup steps, not new owners.
2. Planner MAY compose hybrid/dense/sparse **within** profile constraints; MUST NOT override Skill or re-derive capability from text.
3. Missing Skill when registry non-empty → stop before retrieval; never classify.

---

## Acceptance

- Architecture tests can map each step to an existing owner.
- No `active_production_owner` for “Skill Execution” in 016 registries without exception ADR.
