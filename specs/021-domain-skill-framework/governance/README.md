# Feature 021 — Governance

Domain Skills are a **Domain Pack capability** on the sole Answer + Retrieval path ([ADR-021-001](./adr-021-001-skills-as-domain-pack-capability.md)). They are not a new production owner.

## Capability-only scope

| Allowed | Forbidden |
|---------|-----------|
| Pack YAML under `src/fields/{domain}/skills/` and `profiles/` | `SkillService` or Skill microservice as production owner |
| Additive optional `skill_id` on `/answer` requests | Parallel skill-answer pipeline dual-running with sole path |
| Client Skill buttons / explicit selection | Server auto-selection, intent routing, or fuzzy skill remap |
| Entity-only parse under Skill binding | Embedding metadata filter lists inside Skill YAML |
| `SkillFilterProfile` filters on existing retriever | Dedicated `routes/**/skill*.py` production API owner |
| Trace attributes (`skill_id`, `profile_id`) | Breaking frozen `/answer` **response** fields (015) |

## Distinct profile types

- **Chunk `MetadataProfile`** — `chunk_metadata.yaml`; ingest/enrichment label formatting.
- **`SkillFilterProfile`** — `profiles/*.yaml`; retrieval filter constraints referenced by Skills.

Skills store **profile id references only** — never `filters.field` lists.

## Architecture suite

Run `pytest tests/architecture/test_021_*.py -q` for ADR-021-001 guards:

- No Skill Service or skill route modules
- Frozen `/answer` response contract
- Skill YAML must not embed filter lists

See [ownership-map.md](./ownership-map.md) for concern → owner mapping.
