# Contract: Metadata Profiles (SkillFilterProfile)

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26  
**Authority**: [data-model.md](../data-model.md), research R3/R7

---

## Naming

| Layer | Name |
|-------|------|
| Spec / product | Metadata Profile |
| Pack path | `src/fields/{domain}/profiles/{profile_id}.yaml` |
| Code schema | `SkillFilterProfile` |
| Unrelated existing type | `MetadataProfile` = chunk enrichment (`chunk_metadata.yaml`) |

---

## Profile document (normative)

```yaml
id: drug_interactions
filters:
  field:
    - interactions
  source:
    - leaflet
# optional:
# fallback: { mode: none }   # default when omitted
```

| Field | Required | Semantics |
|-------|----------|-----------|
| `id` | ✅ | Stable profile id |
| `filters.field` | optional | Allow-list of chunk field labels |
| `filters.source` | optional | Allow-list of sources |
| `filters.extra` | optional | Additional parameterized constraints |
| `fallback` | optional | Controlled widen; omit ⇒ **no silent broaden** |

---

## Runtime application

1. Skill resolves → profile id → `effective_filters`.
2. Retriever merges `effective_filters` with entity filters (e.g. grounded medicines) via existing metadata filter pipeline.
3. Hybrid + rerank operate on the filtered candidate set.
4. Zero candidates + no fallback → insufficient-evidence / clarification outcome (not full-corpus search).

---

## Evolution rule

Expanding `filters.field` (e.g. add `warnings`, `precautions`) MUST NOT require Skill id or Skill `profile` reference changes when the Skill already points at that profile.

---

## Acceptance

- Unit: two Skills sharing one profile both observe profile edits.
- Unit: default empty result does not drop filters.
- Architecture: Skills YAML contain no `filters.field` lists.
