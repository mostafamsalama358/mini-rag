# Contract: Skill Registry

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26  
**Authority**: [data-model.md](../data-model.md), [ADR-021-001](../governance/adr-021-001-skills-as-domain-pack-capability.md)

---

## Pack location

```text
src/fields/{domain_key}/skills/{skill_id}.yaml
```

Optional module: absent or empty directory ⇒ domain does not require Skill selection.

---

## Skill document (normative fields)

| Field | Required | Semantics |
|-------|----------|-----------|
| `id` | ✅ | Stable slug; MUST match filename stem |
| `name` | ✅ | Display label |
| `profile` | ✅ | Id of Metadata Profile in same pack `profiles/` |
| `prompt` | ✅ | Template key/path under pack prompts |
| `validation` | ✅ | Object of validation rules (may be `{}`) |
| `output` | optional | Formatting policy |
| `retrieval` | optional | Strategy constraints (non-filter) |
| `capabilities.recommend_mode` | optional | When true, 020 recommend path may apply |

**MUST NOT** include `filters.field` / filter lists — those belong on the Metadata Profile.

---

## Resolution rules

1. Lookup by `(domain_key, skill_id)` exact match.
2. Unknown id → reject; **no** alias, fuzzy, or case-fold remap beyond documented normalization (lowercase slug only if pack declares ids lowercase).
3. Profile missing at load → pack validation failure (fail-fast at startup).
4. UI order = registry declaration order (filename sort or explicit `order` if present).

---

## Pharmacy minimum catalog

Pack MUST expose skill ids:  
`consultations`, `interactions`, `dosage`, `pregnancy`, `lactation`, `contraindications`, `warnings`, `side_effects`, `storage`, `alternatives`, `leaflet`.

---

## Acceptance

- Loader unit tests reject Skills that embed filter lists or dangling profile refs.
- Cross-domain skill_id rejected at request time.
