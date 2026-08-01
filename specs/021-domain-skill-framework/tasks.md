# Tasks: Domain Skill Framework for RAG

**Input**: Design documents from `/specs/021-domain-skill-framework/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, governance/adr-021-001-skills-as-domain-pack-capability.md

**Tests**: Required per constitution (Principle VII). Include unit, integration, and architecture tests. No Skill Service, parallel path, or new sole owner ([ADR-021-001](./governance/adr-021-001-skills-as-domain-pack-capability.md)). No server-side skill/intent/alias routing.

**Organization**: Tasks grouped by user story for independent delivery. Extensions live under Domain Packs, FieldRegistry, Query Understanding, sole RAG answer path, and chat UI only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1â€“US6)
- Every task includes an exact file path

## Path Conventions

- Domain Pack: `src/fields/{domain}/skills/`, `src/fields/{domain}/profiles/`
- Schemas / loader: `src/fields/schemas.py`, `src/services/FieldRegistry.py`
- Query understanding: `src/core/query_parser/`
- Answer path: `src/services/rag/answer_service.py`, `src/services/rag/`
- API: `src/routes/schemes/nlp.py`, `src/routes/nlp.py`, `src/routes/projects.py`
- Chat UI: `src/frontend/js/chat.js`
- Architecture tests: `tests/architecture/`
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Feature artifacts: `specs/021-domain-skill-framework/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold pack directories, governance notes, and architecture suite markers shared by all stories.

- [X] T001 Document Skill capability-only scope (no Skill Service/API/pipeline) in `specs/021-domain-skill-framework/governance/README.md`
- [X] T002 [P] Add pharmacy Skills pack authoring note listing `skills/` + `profiles/` conventions in `src/fields/pharmacy/README_skills.md`
- [X] T003 [P] Create empty directory placeholders `src/fields/pharmacy/skills/.gitkeep` and `src/fields/pharmacy/profiles/.gitkeep`
- [X] T004 [P] Ensure `tests/architecture/README.md` documents 021 suite markers (ADR-021-001, no skill detection, frozen `/answer` response, SkillFilterProfile vs chunk MetadataProfile)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared Pydantic models, FieldRegistry loaders, sole-path architecture guards, and answer-path Skill binding hooks that ALL user stories need. **Blocks all user stories.**

**âš ï¸ CRITICAL**: No user story work begins until this phase is complete.

- [X] T005 Add `SkillDefinition` and `SkillValidationRules` Pydantic models in `src/fields/schemas.py` (fields per `data-model.md`; forbid embedded `filters.field` lists)
- [X] T006 [P] Add `SkillFilterProfile` Pydantic model in `src/fields/schemas.py` (Metadata Profile contract; distinct from existing chunk `MetadataProfile`)
- [X] T007 [P] Add `SelectedSkillBinding` dataclass/model (skill_id, domain_key, resolved skill/profile, effective_filters) in `src/services/rag/skills/binding.py`
- [X] T008 Extend `FieldPack` / `FieldProfile` to carry loaded skills + skill filter profiles in `src/services/FieldRegistry.py`
- [X] T009 Implement pack loaders for `skills/*.yaml` and `profiles/*.yaml` with fail-fast dangling profile refs in `src/services/FieldRegistry.py`
- [X] T010 [P] Add Skill resolution helper (exact id lookup; reject unknown/cross-domain; no fuzzy remap) in `src/services/rag/skills/registry.py`
- [X] T011 [P] Add profileâ†’`effective_filters` normalizer (field/source/extra; default no silent broaden) in `src/services/rag/skills/filters.py`
- [X] T012 Add failing architecture test forbidding Skill Service/API route modules in `tests/architecture/test_021_no_skill_service_or_api.py`
- [X] T013 [P] Add architecture test that frozen `/answer` **response** field names remain unchanged in `tests/architecture/test_021_answer_response_contract_frozen.py` (cite `specs/015-unified-pipeline-migration/contracts/api-stability.md`)
- [X] T014 [P] Add architecture test that Skill YAML must not embed filter lists in `tests/architecture/test_021_skills_no_embedded_filters.py`
- [X] T015 [P] Add unit test stubs (fail-first) for SkillFilterProfile / SkillDefinition validation in `tests/unit/fields/test_skill_schemas.py`
- [X] T016 Document foundational ownership map in `specs/021-domain-skill-framework/governance/ownership-map.md` citing `contracts/ownership-and-pipeline.md`

**Checkpoint**: Models + loaders + sole-path architecture guards exist â€” user stories can proceed.

---

## Phase 3: User Story 1 â€” Interactions Skill end-to-end (Priority: P1) ðŸŽ¯ MVP

**Goal**: Select Interactions, ask `Panadol with Brufen`, get entity extraction + profile-filtered interaction retrieval + grounded answer without intent classification or slash-commands.

**Independent Test**: Pharmacy Skills loaded; `skill_id=interactions` + two-drug query returns interaction-scoped evidence; same text under `dosage` uses dosage profile; no classifier assigns skill.

### Tests for User Story 1

- [X] T017 [P] [US1] Unit test Skill resolve + Interactions profile filters in `tests/unit/services/rag/skills/test_resolve_interactions.py`
- [X] T018 [P] [US1] Unit test entity pair extraction under Interactions Skill (no intent field prediction) in `tests/unit/core/query_parser/test_skill_bound_entities.py`
- [X] T019 [P] [US1] Integration smoke: `POST .../answer` with `skill_id=interactions` and `Panadol with Brufen` keeps frozen response keys in `tests/integration/test_021_interactions_answer.py`
- [X] T020 [P] [US1] Architecture test: no retrieval.yaml intentâ†’skill_id router for Skill-enabled pharmacy in `tests/architecture/test_021_no_intent_skill_router.py`

### Implementation for User Story 1

- [X] T021 [P] [US1] Author `drug_interactions` Metadata Profile in `src/fields/pharmacy/profiles/drug_interactions.yaml`
- [X] T022 [P] [US1] Author `dosage` Metadata Profile in `src/fields/pharmacy/profiles/dosage.yaml` (needed for US1 acceptance: same text under Dosage)
- [X] T023 [P] [US1] Author Interactions Skill YAML in `src/fields/pharmacy/skills/interactions.yaml` (profile + require_medicine_pair + prompt binding)
- [X] T024 [P] [US1] Author Dosage Skill YAML in `src/fields/pharmacy/skills/dosage.yaml`
- [X] T025 [US1] Add additive optional `skill_id` to `AnswerRequest` in `src/routes/schemes/nlp.py`
- [X] T026 [US1] Wire route to pass `skill_id` into answer path in `src/routes/nlp.py`
- [X] T027 [US1] Resolve Skill binding early in answer flow and inject field/operation from Skill in `src/services/rag/answer_service.py`
- [X] T028 [US1] Apply SkillFilterProfile `effective_filters` in retrieval context builder (merge with entity filters; no silent broaden) in `src/services/rag/answer_service.py` and/or `src/services/rag/skills/filters.py`
- [X] T029 [US1] Implement Skill-bound entity-only parse path (Interactions injects field; parser extracts medicines) in `src/core/query_parser/` + pharmacy `src/fields/pharmacy/parser.yaml` skill-bound prompt section
- [X] T030 [US1] Bind Interactions Skill prompt/template for answer generation in `src/fields/pharmacy/answer_generation.yaml` (or pack prompts referenced by Skill)
- [X] T031 [US1] Add structured logging for `skill_id`, `profile_id`, filter summary in `src/services/rag/diagnostics.py`
- [X] T032 [US1] Record `skill_id` + `profile_id` on quality/diagnostic trace surfaces used by answer path in `src/services/rag/` (existing trace/quality context module)

**Checkpoint**: MVP â€” Interactions Skill answers two-drug queries with profile-filtered retrieval on `/answer`.

---

## Phase 4: User Story 2 â€” Skill required before ask (Priority: P1)

**Goal**: Skill-enabled domains reject answers without selection; chat UI requires/sticky-selects Skills via buttons (no slash-commands).

**Independent Test**: Answer without `skill_id` on pharmacy fails closed; UI blocks send until Skill selected; sticky Skill persists across turns.

### Tests for User Story 2

- [X] T033 [P] [US2] Unit test missing `skill_id` rejected when registry non-empty in `tests/unit/services/rag/skills/test_skill_required.py`
- [X] T034 [P] [US2] Integration test: answer without skill_id returns clarification/error (not inferred skill) in `tests/integration/test_021_missing_skill.py`
- [X] T035 [P] [US2] Frontend unit/smoke test or scripted assertion that send is disabled without Skill in `tests/unit/frontend/test_chat_skill_gate.js` (or documented manual checklist under `specs/021-domain-skill-framework/checklists/ui-skill-gate.md` if no JS test runner)

### Implementation for User Story 2

- [X] T036 [US2] Enforce conditional Skill requirement in answer path when `FieldProfile` skills non-empty in `src/services/rag/answer_service.py`
- [X] T037 [US2] Map missing/unknown skill to user-visible clarification/error signal in `src/routes/nlp.py` (preserve 015 response shape)
- [X] T038 [P] [US2] Expose Skill catalog (`id`, `name`, `description?`) on project list/detail payload in `src/routes/projects.py` (and project controller/serializer as needed)
- [X] T039 [US2] Render Skill buttons, require selection before send, sticky `state.selectedSkillId`, include `skill_id` in answer body in `src/frontend/js/chat.js`
- [X] T040 [US2] Update chat HTML/CSS container for Skill button row if present in `src/frontend/` (locate existing chat template/static HTML and extend)

**Checkpoint**: Users cannot ask without selecting a Skill on Skill-enabled domains.

---

## Phase 5: User Story 3 â€” Metadata Profile decoupling (Priority: P1)

**Goal**: Expanding a shared Metadata Profile updates retrieval filters without editing Skill identity; multiple Skills can share one profile.

**Independent Test**: Edit only `profiles/drug_interactions.yaml` filters; Interactions (and any shared Skill) observe new filters; Skill YAML unchanged.

### Tests for User Story 3

- [X] T041 [P] [US3] Unit test profile filter expansion without Skill mutation in `tests/unit/services/rag/skills/test_profile_decoupling.py`
- [X] T042 [P] [US3] Unit test two Skills sharing one profile both see updated filters in `tests/unit/services/rag/skills/test_shared_profile.py`

### Implementation for User Story 3

- [X] T043 [P] [US3] Author remaining pharmacy profiles needed for catalog sharing demos (`warnings.yaml`, `leaflet_general.yaml` stubs OK) in `src/fields/pharmacy/profiles/`
- [X] T044 [US3] Ensure loader caches profile by id and Skills only store profile reference in `src/services/FieldRegistry.py`
- [X] T045 [US3] Document profile evolution rule for pack authors in `src/fields/pharmacy/README_skills.md`
- [X] T046 [US3] Verify retrieval reads filters exclusively from resolved `SkillFilterProfile` (not Skill YAML) in `src/services/rag/skills/filters.py`

**Checkpoint**: Profile-only edits change filter sets; Skills remain stable.

---

## Phase 6: User Story 4 â€” Entity-only parser under Skill (Priority: P1)

**Goal**: Under Pregnancy vs Side Effects, same question yields Skill-injected capability + comparable entity extraction; validation clarifications never switch Skills.

**Independent Test**: `Is Glucophage safe?` under Pregnancy vs Side Effects; Interactions + no medicine â†’ clarification, not skill guess.

### Tests for User Story 4

- [X] T047 [P] [US4] Unit test Skill-injected field for Pregnancy vs Side Effects in `tests/unit/core/query_parser/test_skill_injected_field.py`
- [X] T048 [P] [US4] Unit test Interactions validation clarify on missing medicines in `tests/unit/services/rag/skills/test_skill_validation.py`
- [X] T049 [P] [US4] Architecture test: Skill-enabled path does not call intent classifiers for routing in `tests/architecture/test_021_no_skill_classification.py`

### Implementation for User Story 4

- [X] T050 [P] [US4] Author Pregnancy, Lactation, Side Effects, Contraindications, Warnings, Storage, Leaflet, Consultations Skill YAMLs in `src/fields/pharmacy/skills/`
- [X] T051 [P] [US4] Author matching profiles (`pregnancy`, `lactation`, `side_effects`, `contraindications`, `warnings`, `storage`, `leaflet_general`, `pharmacy_consult`) in `src/fields/pharmacy/profiles/`
- [X] T052 [US4] Implement Skill validation evaluation (`require_medicine`, `require_medicine_pair`, etc.) in `src/services/rag/skills/validation.py`
- [X] T053 [US4] Wire validation failures to clarification prompts (no skill switch) in `src/services/rag/answer_service.py`
- [X] T054 [US4] Finalize Skill-bound parser prompts/rules: entities only; field/operation from Skill in `src/fields/pharmacy/parser.yaml` and `src/core/query_parser/parser.py`
- [X] T055 [US4] Disable/bypass `retrieval.yaml` intent pattern routing when Skill binding present in `src/services/rag/answer_service.py` (or planner entry used by answer path)

**Checkpoint**: Full pharmacy Skill catalog; entity-only parse; validation clarifications work.

---

## Phase 7: User Story 5 â€” Second domain Skills (Priority: P2)

**Goal**: Legal (or stub) Domain Pack Skills appear for legal projects only; unknown/cross-domain skill_id rejected without engine pharmacy hardcoding.

**Independent Test**: Legal project lists legal Skills only; pharmacy skill_id on legal project rejected.

### Tests for User Story 5

- [X] T056 [P] [US5] Unit test domain-scoped Skill catalog isolation in `tests/unit/services/rag/skills/test_domain_skill_catalog.py`
- [X] T057 [P] [US5] Integration test: unknown/cross-domain `skill_id` rejected in `tests/integration/test_021_cross_domain_skill.py`

### Implementation for User Story 5

- [X] T058 [P] [US5] Author stub Legal Skills (`clause_lookup`, `obligations`) in `src/fields/legal/skills/`
- [X] T059 [P] [US5] Author stub Legal profiles in `src/fields/legal/profiles/`
- [X] T060 [US5] Confirm FieldRegistry loads legal skills without pharmacy-specific branches in `src/services/FieldRegistry.py`
- [X] T061 [US5] Ensure project Skill catalog API returns only active domain skills in `src/routes/projects.py`
- [X] T062 [US5] Chat UI loads Skill buttons from project catalog (domain-agnostic) in `src/frontend/js/chat.js`

**Checkpoint**: Domains are Skill plugins; engine stays domain-agnostic.

---

## Phase 8: User Story 6 â€” Recommend only via explicit Skill (Priority: P2)

**Goal**: Alternatives Skill enables 020 recommend-mode; same need text under Leaflet does not auto-enable recommend.

**Independent Test**: Need-based question under `alternatives` vs `leaflet`; only Alternatives runs recommend ranking/safety policy path.

### Tests for User Story 6

- [X] T063 [P] [US6] Unit test `recommend_mode` only when Skill.capabilities.recommend_mode in `tests/unit/services/rag/skills/test_recommend_skill_gate.py`
- [X] T064 [P] [US6] Integration smoke: Alternatives Skill need query vs Leaflet same text in `tests/integration/test_021_recommend_via_skill.py`
- [X] T065 [P] [US6] Architecture test: no auto recommend-intent router when pharmacy skills loaded in `tests/architecture/test_021_no_auto_recommend_intent.py`

### Implementation for User Story 6

- [X] T066 [P] [US6] Author Alternatives Skill + `indications_recommend` profile in `src/fields/pharmacy/skills/alternatives.yaml` and `src/fields/pharmacy/profiles/indications_recommend.yaml`
- [X] T067 [US6] Set `recommend_mode` / Need Frame extraction from Alternatives Skill binding (not free-text intent) in `src/services/rag/answer_service.py` and `src/core/query_parser/parser.py`
- [X] T068 [US6] Remove or gate pharmacy parser auto-recommend intent rules when Skill registry non-empty in `src/fields/pharmacy/parser.yaml`
- [X] T069 [US6] Ensure 020 recommend helpers run only under recommend-capable Skill in `src/services/rag/recommend/` integration points used by answer path
- [X] T070 [US6] Update 020 compatibility note in `specs/021-domain-skill-framework/contracts/compatibility.md` if implementation details need a short â€œas-builtâ€ footnote (keep contract normative)

**Checkpoint**: 020 recommend preserved; classifier entry retired for Skill-enabled pharmacy.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Retirement, observability, quickstart validation, docs.

- [X] T071 [P] Add empty-result / no-silent-broaden unit test in `tests/unit/services/rag/skills/test_no_silent_broaden.py`
- [X] T072 [P] Add structured metrics labels for skill_id/profile_id where answer metrics exist in `src/services/rag/diagnostics.py` (or metrics module used by answer path)
- [X] T073 Deprecate intent-as-skill-router comments/paths in `src/fields/pharmacy/retrieval.yaml` (document non-authoritative for Skill-enabled domains; do not delete unrelated exhaustive-list heuristics without review)
- [X] T074 [P] Run and record `quickstart.md` drill results in `specs/021-domain-skill-framework/governance/quickstart-results.md`
- [X] T075 [P] Update `AGENTS.md` Related blurb if implementation package paths diverge from plan (keep SPECKIT plan pointer at `specs/021-domain-skill-framework/plan.md`)
- [X] T076 Verify generic domain with empty skills/ remains backward-compatible (no skill_id required) in `tests/integration/test_021_generic_no_skills.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies â€” start immediately
- **Foundational (Phase 2)**: Depends on Setup â€” **BLOCKS** all user stories
- **US1 (Phase 3)**: After Foundational â€” MVP
- **US2 (Phase 4)**: After Foundational; integrates with US1 API `skill_id` (can start UI catalog after T025/T038 foundations)
- **US3 (Phase 5)**: After Foundational; strongest after US1 profiles exist
- **US4 (Phase 6)**: After Foundational; completes full pharmacy catalog + parser mode
- **US5 (Phase 7)**: After Foundational; best after US2 catalog API exists
- **US6 (Phase 8)**: After Foundational; best after US1 answer binding + US4 parser mode
- **Polish (Phase 9)**: After desired stories complete

### User Story Dependencies

| Story | Depends on | Independently testable? |
|-------|------------|-------------------------|
| US1 Interactions E2E | Phase 2 | Yes (MVP) |
| US2 Skill required + UI | Phase 2; uses `skill_id` from US1 schema | Yes (API reject without UI) |
| US3 Profile decoupling | Phase 2; uses profiles from US1 | Yes (unit-level) |
| US4 Entity-only parser | Phase 2 | Yes |
| US5 Legal stub domain | Phase 2; catalog API from US2 | Yes |
| US6 Recommend via Skill | Phase 2; answer binding from US1 | Yes |

### Within Each User Story

- Tests (fail-first) before implementation where listed
- Pack YAML / models before wiring
- Services before routes/UI
- Story complete before next priority when single-threaded

### Parallel Opportunities

- Phase 1: T002â€“T004 in parallel
- Phase 2: T006â€“T007, T010â€“T011, T013â€“T015 in parallel after T005/T008 sequencing
- US1: T017â€“T020 tests parallel; T021â€“T024 YAML parallel
- US2: T033â€“T035 tests parallel; T038 parallel with T036/T037 after schema exists
- US3: T041â€“T042 parallel
- US4: T047â€“T049 parallel; T050â€“T051 YAML parallel
- US5: T056â€“T057 parallel; T058â€“T059 YAML parallel
- US6: T063â€“T065 parallel
- After Phase 2, US3 unit work can proceed in parallel with US1 if staffed

---

## Parallel Example: User Story 1

```text
# Tests (parallel):
T017 Unit test Skill resolve + Interactions profile filters
T018 Unit test entity pair extraction under Interactions
T019 Integration smoke interactions answer
T020 Architecture test no intentâ†’skill router

# Pack YAML (parallel):
T021 profiles/drug_interactions.yaml
T022 profiles/dosage.yaml
T023 skills/interactions.yaml
T024 skills/dosage.yaml

# Then sequential wiring:
T025 â†’ T026 â†’ T027 â†’ T028 â†’ T029 â†’ â€¦
```

---

## Parallel Example: User Story 4

```text
# Tests (parallel):
T047 skill-injected field Pregnancy vs Side Effects
T048 Interactions validation clarify
T049 no skill classification architecture guard

# Pack YAML (parallel):
T050 remaining pharmacy skills/*
T051 remaining pharmacy profiles/*
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**critical**)
3. Complete Phase 3: US1 Interactions E2E
4. **STOP and VALIDATE** Independent Test for US1
5. Demo `/answer` with `skill_id=interactions`

### Incremental Delivery

1. Setup + Foundational â†’ foundation ready
2. US1 â†’ MVP Interactions path
3. US2 â†’ mandatory selection + chat buttons
4. US3 â†’ profile decoupling proof
5. US4 â†’ full pharmacy catalog + entity-only parser
6. US5 â†’ legal stub domain plugin proof
7. US6 â†’ 020 recommend via Alternatives only
8. Polish â†’ retirement, quickstart results, generic compat

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Dev A: US1 â†’ US2
   - Dev B: US3 + US4 pack YAML/parser
   - Dev C: US5 stubs + US6 recommend gate
3. Integrate on sole answer path; keep architecture tests green

---

## Notes

- [P] = different files, no dependencies on incomplete tasks
- [Story] maps to US1â€“US6 in `spec.md`
- Chunk `MetadataProfile` (`chunk_metadata.yaml`) MUST remain distinct from `SkillFilterProfile` (`profiles/*.yaml`)
- Do not create `routes/**/skill*.py` production Skill API owner â€” catalog may extend existing projects routes only
- Commit after each task or logical group
- Stop at checkpoints to validate independently
- Next command after tasks: `/speckit-implement` (or implement MVP manually from Phase 1â€“3)
