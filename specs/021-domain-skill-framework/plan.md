# Implementation Plan: Domain Skill Framework for RAG

**Branch**: `enhance/query` (feature directory independent) | **Date**: 2026-07-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-domain-skill-framework/spec.md`

**Note**: This plan designs Domain Skills as a **Domain Pack capability** on the sole Answer + Retrieval path. It does **not** authorize a Skill Service, parallel answer path, or new sole owner ([ADR-021-001](./governance/adr-021-001-skills-as-domain-pack-capability.md)).

---

## Summary

Introduce **explicit Domain Skills** so users select a retrieval capability (Interactions, Dosage, Pregnancy, …) before asking. The selected Skill is the sole router; Query Understanding extracts entities/slots only; Skills reference **Metadata Profiles** (retrieval filter packs) so schema can evolve without Skill renames.

Technical approach (from [research.md](./research.md)):

1. Extend Domain Packs (`src/fields/{domain}/`) with `skills/` + `profiles/` (Skill Metadata Profiles).
2. Load/validate via `FieldRegistry` as optional pack modules; expose Skill catalog to UI/API.
3. Add additive `skill_id` on answer requests; require it when the pack’s Skill registry is non-empty.
4. Resolve Skill → Metadata Profile → retrieval filters before hybrid search; inject Skill-owned field/operation/prompt/validation into the sole path.
5. Narrow parser under Skill: entity extraction + grounding; **no** intent/skill/alias classification for routing.
6. Map 020 recommend-mode to explicit Skills (e.g. `alternatives`); retire auto recommend/intent routing for Skill-enabled domains.
7. Trace `skill_id` + profile id on 018 quality/diagnostic surfaces; skill-scoped eval under 019 later.

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic, Celery; existing LLM / embedding / vector / reranker factories; Domain Pack YAML under `src/fields/`

**Storage**: PostgreSQL + pgvector (unchanged chunk metadata); Skill/Profile definitions are pack YAML (not a new DB sole-source). Project domain already on `projects.domain_key`.

**Testing**: pytest + pytest-asyncio; unit tests for Skill resolution, missing/unknown Skill rejection, profile filter merge, entity-only parse under Skill, no classifier invocation; architecture tests for sole-path / no skill-detection; integration smokes for `/answer` with `skill_id` + chat Skill UI

**Target Platform**: Linux server / Docker Compose (AlgoRAG production stack)

**Project Type**: Web service (FastAPI) + Domain Pack configuration + lightweight chat UI (`src/frontend/js/chat.js`); capability extension (not a new deployable service)

**Performance Goals**: Skill-scoped retrieval SHOULD cut irrelevant-field candidates ≥30% on Interactions eval set and improve end-to-end answer latency ≥15% vs unconstrained search (spec SC-002/SC-003); no mandatory extra LLM round-trip beyond existing parse/compose

**Constraints**:
- ADR-021-001 / 016 M0: no Skill Service, parallel path, or new sole owner
- 015 frozen **response** field-level contract; request MAY gain additive `skill_id` ([contracts/api-and-ui.md](./contracts/api-and-ui.md))
- Existing `fields.schemas.MetadataProfile` = **chunk** metadata (`chunk_metadata.yaml`) — Skill “Metadata Profiles” MUST use a distinct schema/type name in code (`SkillFilterProfile`) to avoid collision (research R3)
- 018 grounding + Quality Context/Trace; 019 owns eval runners
- No silent broadening when profile filters yield empty candidates (unless profile defines controlled fallback)

**Scale/Scope**: Pharmacy Skill catalog (11 Skills) + shared/reusable filter profiles; Legal/Finance prove pack model with optional stub registries; engine remains domain-agnostic

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ✅ Pack YAML + application resolution; vector filters via existing stores |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ `specs/021-…` + pack modules + tests under existing trees |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ✅ No new provider type; Domain Pack Open/Closed extension |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic schemas | ✅ Additive typed request field; Skill/Profile Pydantic models |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ Skills constrain targets; hybrid+rerank+citations remain |
| G6 Testing | Unit and integration tests planned for changed behavior | ✅ See Validation Strategy |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ skill_id + profile_id in logs/trace |
| G8 Security | No secrets in code; input validation; parameterized SQL | ✅ Skill id allow-list from registry; filters parameterized |
| G9 Performance | Long work in Celery; batching/pooling considered | ✅ Answer-path only; packs load at startup |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ Unchanged |

*Any unchecked gate requires justification in Complexity Tracking below.*

**Pre-Phase-0 gate result**: PASS

**Post-Phase-1 gate result**: PASS (design adds pack modules + additive API/UI only; no new owners or dual path)

---

## Project Structure

### Documentation (this feature)

```text
specs/021-domain-skill-framework/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/              # Phase 1
│   ├── ownership-and-pipeline.md
│   ├── skill-registry.md
│   ├── metadata-profiles.md
│   ├── query-understanding.md
│   ├── api-and-ui.md
│   └── compatibility.md
├── governance/
│   └── adr-021-001-skills-as-domain-pack-capability.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md                # NOT created by /speckit-plan
```

### Source Code (repository root)

Extension points (existing trees — no new top-level service package):

```text
src/fields/{domain}/
  skills/*.yaml             # Skill definitions (Domain Pack)
  profiles/*.yaml           # Skill Metadata Profiles / filter profiles
src/fields/schemas.py       # SkillDefinition + SkillFilterProfile models
src/services/FieldRegistry.py
src/core/query_parser/      # Entity-only mode when skill_id bound
src/services/rag/           # Skill resolve → profile filters → sole answer path
src/routes/schemes/nlp.py   # Additive AnswerRequest.skill_id
src/routes/                 # Skill catalog exposure for UI
src/frontend/js/chat.js     # Skill buttons + sticky selection
tests/unit/
tests/integration/
tests/architecture/         # No skill-detection / sole-path guards
```

**Structure Decision**: Extend Domain Packs + sole RAG orchestrator (same pattern as 020). Skills/profiles are pack artifacts; resolution lives in FieldRegistry + answer path. UI is the existing chat frontend.

---

## Complexity Tracking

> No constitution violations requiring justification.

| Note | Handling |
|------|----------|
| Name collision: existing `MetadataProfile` (chunk) vs Skill Metadata Profiles | Code type `SkillFilterProfile`; pack dir `profiles/`; contracts keep user term “Metadata Profile” |
| 015 frozen request schema vs required Skill | Additive optional field; **conditionally required** when registry non-empty — documented as compatible additive contract, not a frozen-field rename |

---

## Phase 0 / Phase 1 Outputs

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/](./contracts/) |
| ADR | [governance/adr-021-001-skills-as-domain-pack-capability.md](./governance/adr-021-001-skills-as-domain-pack-capability.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

---

## Validation Strategy

| Layer | Focus |
|-------|--------|
| Unit | Skill registry load/validate; unknown/missing skill; profile filter resolution; entity-only parse fixtures; recommend_mode only when Skill declares it |
| Architecture | No intent/skill classifier path for Skill-enabled domains; no new sole owner; filters not embedded in Skill YAML |
| Integration | `POST .../answer` with `skill_id=interactions` + two-drug query; rejection without skill when registry non-empty; chat sends selected skill |
| Eval bridge | Skill-scoped golden sets / gates owned under 019 (catalog only here) |

---

## Implementation Phases (for `/speckit-tasks`)

1. **Pack schemas + loader** — SkillDefinition, SkillFilterProfile, FieldRegistry load `skills/` + `profiles/`
2. **Pharmacy catalog** — 11 Skills + shared profiles (interactions, dosage, pregnancy, …)
3. **Answer-path binding** — resolve skill → inject field/operation/filters/prompt/validation; quality trace fields
4. **Parser entity-only mode** — Skill-bound parse prompts/schema; disable intent routing
5. **API + UI** — additive `skill_id`; catalog endpoint/payload; chat Skill buttons
6. **020 bridge** — Alternatives Skill → recommend capability; remove auto recommend intent for Skill-enabled pharmacy
7. **Tests + retirement** — architecture guards; deprecate retrieval.yaml intent routing as skill router

---

## Next Command

`/speckit-tasks` — generate dependency-ordered implementation tasks from this plan.
