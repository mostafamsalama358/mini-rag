# Contract: API and UI (Skill Selection)

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26  
**Authority**: [spec.md](../spec.md) FR-002/FR-003/FR-019; Feature 015 api-stability (response frozen)

---

## Answer request (additive)

Endpoint remains the existing answer route (e.g. `POST /api/v1/nlp/index/answer/{project_id}`).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | ✅ | Unchanged |
| `limit` | int | optional | Unchanged |
| `session_id` | string | optional | Unchanged |
| `metadata_filter` | object | optional | Unchanged (client pre-filter; Skill profile filters apply in addition) |
| `skill_id` | string \| null | **conditionally required** | Required when Domain Pack Skill registry is non-empty |

### Conditional requirement

| Pack skills | `skill_id` missing | Behavior |
|-------------|--------------------|----------|
| Non-empty | yes | Reject / clarification — **no** classify |
| Non-empty | unknown id | Reject — **no** fuzzy remap |
| Empty / absent | any | Prior behavior (skill not required) |

### Response

Frozen 015 success/error field-level contract unchanged. Skill diagnostics are not new mandatory public response fields (trace/logs only unless a future API ADR adds them).

Suggested internal/error signal (implementation may map to existing clarification patterns):

| Condition | User-visible behavior |
|-----------|----------------------|
| Missing skill | Prompt to select a Skill |
| Unknown skill | Clear invalid-skill error |
| Validation fail | Clarification for missing entities |

---

## Skill catalog for UI

Clients MUST obtain the ordered Skill list for the active project’s domain (ids + labels + optional descriptions). Delivery options (either acceptable):

1. Include `skills: [{id, name, description?}]` on project list/detail payloads, or
2. Dedicated read endpoint scoped by `project_id` / domain.

Catalog MUST reflect pack registry only — never inferred from query text.

---

## Chat UI contract

| Behavior | Requirement |
|----------|-------------|
| Skill controls | Buttons (or equivalent) for each catalog Skill |
| Before send | Skill MUST be selected when catalog non-empty |
| Slash commands | NOT required; MUST NOT be the only selection method |
| Sticky selection | Selected Skill remains until user changes it |
| Wire | Every answer call includes `skill_id` |

---

## Acceptance

- Integration: answer without `skill_id` on pharmacy project fails closed.
- UI: Interactions click + `Panadol with Brufen` sends `skill_id=interactions`.
- Response JSON keys for success path remain 015-compatible.
