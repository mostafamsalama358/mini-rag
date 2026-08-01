# Quickstart: Domain Skill Framework (Architecture Validation)

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26

Architecture-review drills proving the Skill design — not a coding sprint. Implementation belongs to `/speckit-tasks` and later implement.

---

## Prerequisites

- Read [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md)
- Skim [contracts/](./contracts/)
- Read [ADR-021-001](./governance/adr-021-001-skills-as-domain-pack-capability.md)
- Related: `specs/002-…`, `specs/004-…`, `specs/015-…`, `specs/016-…`, `specs/018-…`, `specs/020-…`

---

## 1. Sole-Path & ADR Drill (FR-013, SC-007)

**Steps**:

1. Confirm ADR-021-001 rejects Skill Service, parallel path, new sole owner.
2. Walk [ownership-and-pipeline](./contracts/ownership-and-pipeline.md); map each step to an existing owner.
3. Confirm no new production orchestrator is mandated.

**Expected**: Capability-only; M0 freeze respected.

---

## 2. Explicit Selection Drill (US1, US2)

**Scenario**: User selects **Interactions**, types `Panadol with Brufen`.

**Steps**:

1. Assert request carries `skill_id=interactions` (UI or API client).
2. Assert no intent/skill classifier assigns the Skill.
3. Assert parser extracts both medicines; Skill injects interaction capability.
4. Assert answer without `skill_id` on Skill-enabled pharmacy is rejected/prompted.

**Expected**: Deterministic Skill binding; slash-command not required.

---

## 3. Metadata Profile Decoupling Drill (US3, FR-007)

**Steps**:

1. Note Interactions Skill references profile `drug_interactions` only (no filter list in Skill).
2. Expand profile `filters.field` to include `warnings` / `precautions`.
3. Confirm Skill identity unchanged.

**Expected**: Profile edit only; Skills stable.

---

## 4. Naming Collision Drill (research R3)

**Steps**:

1. Distinguish chunk `MetadataProfile` (`chunk_metadata.yaml`) from Skill Metadata Profile (`SkillFilterProfile` / `profiles/*.yaml`).
2. Confirm plan/contracts document both.

**Expected**: No single type overloaded for both concerns.

---

## 5. Same Text, Different Skill Drill (US4)

**Scenario**: `Is Glucophage safe?` under Pregnancy vs Side Effects.

**Steps**:

1. Same entities; different Skill-injected field/profile.
2. Confirm no auto skill switch from the word “safe”.

**Expected**: Skill remains source of truth.

---

## 6. Empty Filter Result Drill (FR-020)

**Steps**:

1. Apply a narrow profile that matches zero chunks for a query.
2. Confirm system does **not** silently search full corpus (unless profile fallback declared).

**Expected**: Insufficient-evidence / clarification path.

---

## 7. 020 Recommend Bridge Drill (US6)

**Scenario**: Need-based question under Alternatives vs Leaflet.

**Steps**:

1. Alternatives → recommend policies may apply.
2. Leaflet + same text → no auto `recommend_mode`.

**Expected**: Explicit Skill gates recommend capability.

---

## 8. Frozen Response Contract Drill (FR-019)

**Steps**:

1. Diff against [api-and-ui](./contracts/api-and-ui.md) and 015 api-stability.
2. Confirm success response keys unchanged; `skill_id` is request-only.

**Expected**: No wire break on response.

---

## 9. Cross-Domain Rejection Drill (US5)

**Steps**:

1. Pharmacy project + `skill_id` from legal catalog → reject.
2. Legal project shows legal Skills only (stub catalog acceptable for design review).

**Expected**: No cross-domain aliasing.

---

## Exit criteria

| Check | Pass? |
|-------|-------|
| ADR / sole-path clear | ☐ |
| Explicit selection / no classifier | ☐ |
| Profile decoupling | ☐ |
| Naming collision documented | ☐ |
| Empty-result no silent broaden | ☐ |
| 020 via Alternatives only | ☐ |
| 015 response frozen | ☐ |

When all checked, proceed to `/speckit-tasks`.
