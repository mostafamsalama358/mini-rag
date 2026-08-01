# Pharmacy Domain Skills (021)

Pack modules:

- `skills/*.yaml` — Skill definitions (`profile` ref, validation, `field`/`operation`, capabilities)
- `profiles/*.yaml` — Skill Metadata Profiles (`SkillFilterProfile` filters)

**Rules**

- Skills MUST NOT embed `filters:` — put filters on profiles.
- Expand profile `filters.field` without renaming Skills.
- `alternatives` sets `capabilities.recommend_mode: true` (020 entry).
- Engine loads via `FieldRegistry`; no pharmacy hardcoding in core.
