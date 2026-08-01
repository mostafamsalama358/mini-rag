# Contract: API and UI Compatibility

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28  
**Depends on**: 015 frozen response contract; 021 additive `skill_id` + Skill UI

---

## Frozen / preserved

| Surface | Rule |
|---------|------|
| `/answer` **response** fields | Unchanged (015) |
| Request `skill_id` | Additive; same meaning as 021 |
| Skill IDs | Existing pack ids preserved |
| Skill packs YAML ids/profiles | Compatible; remove only bridge fields (`plan_field`/`plan_operation`) if present |
| Chat Skill buttons | Continue to send selected `skill_id` |
| Skill catalog payload | id / name / description (or equivalent) preserved |

## Internal-only changes

- Unified pipeline native Skill binding  
- Stage/strategy registries  
- Removal of legacy Skill bypass  
- Removal of QueryPlan bridge for Skill traffic  

## Acceptance

- Existing 021 API/UI compatibility tests remain green (updated only for internal moves).
- No client change required for Skill selection UX.
