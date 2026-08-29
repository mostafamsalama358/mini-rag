# Madrsty Domain Skills (021)

UI is two-level; the API still sends **one** `skill_id`.

1. Subject chips (`subject` / `subject_label`) — Geography, French, …
2. Intent chips for that subject (`name` / `intent`) — Explain, Grammar, …
3. `/answer` body includes `skill_id` such as `geography_explain`.

Pack modules:

- `skills/*.yaml` — Skill definitions (`subject`, `intent`, `profile` ref). No `filters:`.
- `profiles/*.yaml` — `SkillFilterProfile` with `extra.subject`. Geography v1 is subject-only (corpus is mostly unlabeled). French still adds `field` (grammar, vocabulary, …).

v1 subjects: Geography, French. Add later subjects as more `subject_*` YAML pairs.
