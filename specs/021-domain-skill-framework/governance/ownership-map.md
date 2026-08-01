# Ownership map (021)

| Concern | Owner |
|---------|--------|
| Skill / SkillFilterProfile YAML | Domain Pack (`src/fields/{domain}/`) |
| Pack load | `FieldRegistry` |
| Client `skill_id` | Presentation / UI |
| Resolve + validation + filter merge | `src/services/rag/skills/` on sole answer path |
| Entity extraction | Query Understanding |
| Hybrid retrieval + rerank | Retrieval |
| Answer text | Answer Generation |
| Eval runners | Feature 019 |

See [contracts/ownership-and-pipeline.md](../contracts/ownership-and-pipeline.md) and [ADR-021-001](./adr-021-001-skills-as-domain-pack-capability.md).
