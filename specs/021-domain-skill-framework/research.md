# Research: Domain Skill Framework for RAG

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26

Phase 0 decisions resolving planning unknowns. Aligns with [spec.md](./spec.md) and [ADR-021-001](./governance/adr-021-001-skills-as-domain-pack-capability.md).

---

## R1 — Skills as Domain Pack capability (not Service / parallel path)

**Decision**: Domain Skills are a **Domain Pack capability** composed on the sole Answer + Retrieval path. No Skill Service, no parallel Skill pipeline, no new sole owner.

**Rationale**: Spec architecture stance; 016 M0 freeze; same pattern as ADR-020-001 for recommendation.

**Alternatives considered**:
- Dedicated Skill microservice / orchestrator — rejected (new owner, M0 violation)
- Skills as a second answer API — rejected (015/016 dual-path risk)
- Capability composition on sole path (**selected**)

---

## R2 — Explicit Skill selection vs automatic routing

**Decision**: Client-supplied `skill_id` is the **only** authority for capability routing. Server MUST NOT run intent classification, skill classification, alias resolution, command detection, or semantic routing to choose/replace the Skill.

**Rationale**: Spec FR-004/FR-005 and primary product goal (determinism). Existing `retrieval.yaml` intent patterns and parser field/intent mapping become non-authoritative for Skill-enabled domains.

**Alternatives considered**:
- Hybrid: UI skill + server re-classify on conflict — rejected (reintroduces non-determinism)
- Slash-commands (`/Interactions`) as primary UX — rejected (spec: UI buttons; no typing skill names required)
- Soft default Skill when missing — rejected for domains with non-empty registry (must require selection)

---

## R3 — Naming: Skill “Metadata Profile” vs existing `MetadataProfile`

**Decision**:
- **Contracts / UX language**: keep “Metadata Profile” (spec term).
- **Code / schema**: introduce `SkillFilterProfile` (or equivalent) loaded from `src/fields/{domain}/profiles/*.yaml`.
- **Existing** `fields.schemas.MetadataProfile` remains the **chunk metadata / enrichment** model for `chunk_metadata.yaml` — unchanged.

**Rationale**: Avoid colliding two different concepts under one Python type. Spec’s decoupling goal is about retrieval filters, not chunk enrichment.

**Alternatives considered**:
- Rename chunk `MetadataProfile` — rejected (large blast radius, out of scope)
- Put filters inside Skill YAML — rejected (spec FR-007)
- Call pack dir `filter_profiles/` only — acceptable alias; prefer `profiles/` per product description with typed schema name disambiguation

---

## R4 — Pack layout and loader ownership

**Decision**: Skills and profiles live under each Domain Pack:

```text
src/fields/{domain}/
  skills/{skill_id}.yaml
  profiles/{profile_id}.yaml
```

`FieldRegistry` loads them as **optional** pack modules at startup (same lifecycle as other YAML). Empty/absent `skills/` ⇒ Skills not required for that domain (backward compatible).

**Rationale**: Spec domain independence; aligns with 002 Field Registry Open/Closed extension; no engine hardcoding of pharmacy skill lists.

**Alternatives considered**:
- DB-only Skill definitions — rejected for v1 (packs are SoT; projects already snapshot config_json)
- Top-level `domains/` tree separate from `src/fields/` — rejected (duplicates Field Registry)

---

## R5 — QueryPlan under Skills

**Decision**: When `skill_id` is bound:

1. Resolve Skill → set capability fields on the plan from the Skill (`field` / `operation` / `recommend_mode` / prompt binding) — **not** from LLM intent prediction.
2. Parser extracts **entities / slots** (and Need Frame slots only if the Skill declares recommend capability).
3. Planner/Engine consume Skill-resolved Metadata Profile filters; MUST NOT re-infer skill from text.

**Rationale**: Spec parser responsibility + sole-path reuse of QueryPlan consumers. Minimizes schema churn while removing intent-as-router.

**Alternatives considered**:
- Replace QueryPlan entirely with SkillContext — rejected (larger blast radius across 009/010)
- Keep LLM predicting `field` even with Skill — rejected (dual authority)

---

## R6 — API contract: additive `skill_id`

**Decision**: Add optional `skill_id: string | null` to `AnswerRequest`. When the project’s Domain Pack Skill registry is **non-empty**, `skill_id` is **conditionally required**; missing/unknown → structured error / clarification signal (no silent classify).

**Response** schema remains 015-frozen. Skill catalog exposed via project payload and/or a small read endpoint for UI buttons.

**Rationale**: Spec FR-002/FR-019; 015 freezes response fields and pre-migration request shape — additive request fields for new capability are the established extension pattern (session_id, metadata_filter already optional).

**Alternatives considered**:
- Encode skill in `metadata_filter` — rejected (overloads unrelated concern; weak validation)
- Break/rename frozen response fields to surface skill — rejected (015)
- Require skill for all domains including empty registry — rejected (breaks generic)

---

## R7 — Filter application and empty-result policy

**Decision**: Retriever applies profile filters (e.g. `field IN […]`, optional `source`) via existing metadata filter mechanisms. Default: **no silent broadening** to full corpus when zero candidates; return insufficient-evidence / clarification. Controlled fallback only if the profile explicitly declares it.

**Rationale**: Spec FR-011/FR-020; precision and latency goals depend on keeping filters honest.

**Alternatives considered**:
- Auto-widen on empty — rejected as default (hides bad profiles; reintroduces noise)
- Skill-level filter lists — rejected (coupling)

---

## R8 — Pharmacy catalog and 020 bridge

**Decision**: Ship pharmacy Skills: consultations, interactions, dosage, pregnancy, lactation, contraindications, warnings, side_effects, storage, alternatives, leaflet. **`alternatives`** (and optionally consultations if pack marks recommend) is the only entry to 020 recommend-mode. Auto `recommend_mode` from free-text intent is disabled for Skill-enabled pharmacy.

**Rationale**: Spec FR-016/FR-017; preserves 020 value without classifier.

**Alternatives considered**:
- Keep auto recommend intent alongside Skills — rejected (dual router)
- Merge all leaflet sections into one Skill — rejected (defeats precision goal)

---

## R9 — UI sticky Skill

**Decision**: Chat UI shows Skill buttons, requires selection before send, keeps selection sticky until user changes it; each API call still sends `skill_id`.

**Rationale**: Spec Assumptions; matches FR-003; simple mental model for pharmacists.

**Alternatives considered**:
- Clear Skill every turn — worse UX
- Server-side session Skill store as sole authority — rejected (client selection is SoT; session may assist UX only)

---

## R10 — Intent YAML retirement

**Decision**: For Skill-enabled domains, `retrieval.yaml` intent pattern matching MUST NOT select Skill/field capability. Patterns may remain temporarily for non-Skill domains or exhaustive-list heuristics unrelated to skill routing, but skill routing authority is exclusively `skill_id`.

**Rationale**: 016 forbids lasting dual routers; spec SC-007.

**Alternatives considered**:
- Run intents then override with Skill — rejected (wasted work; conflict surface)

---

## Resolved Technical Context

| Item | Resolution |
|------|------------|
| Target Platform | Linux / Docker Compose AlgoRAG stack |
| Project Type | FastAPI web service + Domain Pack YAML + chat JS |
| Performance Goals | ≥30% irrelevant-candidate reduction; ≥15% latency improvement on skill-scoped sets |
| Constraints | Sole path; additive API; SkillFilterProfile naming; no silent broaden |
| Scale/Scope | Pharmacy 11 Skills first; other domains via pack stubs |
