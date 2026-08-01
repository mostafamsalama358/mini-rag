# Data Model: Domain Skill Framework

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26  
**Authority**: [spec.md](./spec.md), [research.md](./research.md)

Logical entities for Skills and Metadata Profiles. Pack YAML is the authoring source of truth; runtime views are immutable pack snapshots (FieldRegistry lifecycle).

---

## Entity Relationship (logical)

```text
Domain Pack
  ├── Skill Registry (1..n Skill)
  │     └── references → Metadata Profile (SkillFilterProfile)
  ├── Metadata Profiles (1..n)
  └── (existing) chunk MetadataProfile / fields / parser / …

Request
  └── Selected Skill Binding (skill_id) → Skill → Metadata Profile → Retrieval Filters
```

---

## Skill

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | string | ✅ | Stable slug (e.g. `interactions`); UI may show localized `label` |
| `name` / `label` | string | ✅ | Display name (e.g. Interactions) |
| `profile` | string | ✅ | Metadata Profile id (`SkillFilterProfile`) |
| `prompt` | string | ✅ | Prompt/template key or relative pack path (versioned) |
| `validation` | object | ✅ | See Validation Rules |
| `output` | object | optional | Formatting policy hooks (sections, tone, list vs prose) |
| `retrieval` | object | optional | Strategy constraints within sole path (e.g. prefer hybrid; top-k hints) |
| `capabilities` | object | optional | Flags: `recommend_mode`, `require_need_frame`, … |
| `description` | string | optional | UI helper text |

**Invariants**:
- `id` unique within domain.
- MUST reference an existing profile in the same pack.
- MUST NOT embed metadata filter field lists (those belong on the profile).

---

## Metadata Profile (SkillFilterProfile)

User/contract term: **Metadata Profile**.  
Implementation type name: **`SkillFilterProfile`** (avoids collision with chunk `MetadataProfile`).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | string | ✅ | e.g. `drug_interactions` |
| `filters` | object | ✅ | Retrieval constraints |
| `filters.field` | string[] | optional | Chunk metadata `field` / `field_name` allow-list |
| `filters.source` | string[] | optional | e.g. `leaflet`, `catalog` |
| `filters.extra` | object | optional | Additional keyed constraints (parameterized) |
| `fallback` | object | optional | Controlled widen policy; **absent ⇒ no silent broaden** |
| `notes` | string | optional | Maintainer documentation |

**Invariants**:
- Multiple Skills MAY share one profile.
- Changing filters MUST NOT require Skill id changes.
- Unknown filter keys fail validation at pack load (fail-fast) or are ignored with logged warning per pack policy — choose fail-fast for required keys.

---

## Skill Registry

| Attribute | Type | Notes |
|-----------|------|-------|
| `domain_key` | string | Pack key (`pharmacy`, `legal`, …) |
| `skills` | Skill[] | Ordered for UI presentation |
| `requires_selection` | bool | Derived: `len(skills) > 0` |

---

## Selected Skill Binding (per request)

| Attribute | Type | Notes |
|-----------|------|-------|
| `skill_id` | string | Client-supplied; authoritative |
| `domain_key` | string | From project |
| `resolved_skill` | Skill | Registry lookup |
| `resolved_profile` | SkillFilterProfile | From skill.profile |
| `effective_filters` | object | Normalized filters for vector/text search |

**Transitions**:
1. Missing `skill_id` + registry non-empty → reject / prompt (no resolve).
2. Unknown `skill_id` → reject (no fuzzy remap).
3. Valid → bind for parse → retrieve → answer.

---

## Parsed Entities / Slots

| Attribute | Type | Notes |
|-----------|------|-------|
| `entities` | string[] | Grounded medicines / domain entities |
| `entity` | string \| null | Primary entity convenience |
| `need_frame` | object \| null | Only when Skill.capabilities.recommend_mode |
| `language` | string | ISO 639-1 |

Under Skill binding, capability routing fields (`field`, `operation`, `recommend_mode`) are **Skill-injected**, not classifier-predicted.

---

## Validation Rules (Skill.validation)

| Rule key | Meaning | Example |
|----------|---------|---------|
| `require_medicine` | ≥1 grounded medicine entity | Dosage, Pregnancy |
| `require_medicine_pair` | ≥2 distinct medicines | Interactions |
| `require_need` | Need Frame / need text present | Alternatives |
| `min_entities` / `max_entities` | Numeric bounds | — |
| `custom` | Pack-declared structured checks | Future |

Failure → clarification / structured validation error; **never** switch Skill.

---

## Pharmacy Seed Catalog (normative ids)

| skill_id | profile (initial) | Notes |
|----------|-------------------|-------|
| `consultations` | `pharmacy_consult` | Broader counseling profile |
| `interactions` | `drug_interactions` | Pair validation |
| `dosage` | `dosage` | |
| `pregnancy` | `pregnancy` | |
| `lactation` | `lactation` | |
| `contraindications` | `contraindications` | |
| `warnings` | `warnings` | |
| `side_effects` | `side_effects` | |
| `storage` | `storage` | |
| `alternatives` | `indications_recommend` | 020 recommend capability |
| `leaflet` | `leaflet_general` | Wider leaflet scope |

Profile filter sets may expand later without renaming Skills.

---

## Trace attributes (018)

| Attribute | Where |
|-----------|--------|
| `skill_id` | Quality Trace / structured logs |
| `profile_id` | Quality Trace / structured logs |
| `skill_validation_outcome` | ok \| clarify \| reject |
| `filters_applied` | Diagnostic (not mandatory public API) |

---

## Non-entities (explicit)

- No Skill DB table required for v1 (pack YAML + project domain_key).
- No Intent / Alias entity for routing.
- Chunk storage metadata schema unchanged (ingest still writes `field`, `source`, …).
