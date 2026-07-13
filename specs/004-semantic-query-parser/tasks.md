# Tasks: Semantic Query Parser

**Input**: Design documents from `/specs/004-semantic-query-parser/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/query-understanding.md, quickstart.md

**Tests**: Per constitution (Principle VII), unit and integration tests are REQUIRED for changed behavior. Golden-set regression required per spec FR-020 / SC-002.

**Organization**: Tasks grouped by user story (US1–US5 from spec.md). Foundational phase delivers the parser module; each story phase wires or validates one independent journey.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Spec user story (US1–US5). Setup, foundational, and polish tasks have NO story label.
- Every task lists an exact file path

## Path Conventions

- Source: `src/` at repository root
- Tests: `tests/` at repository root
- Golden set: `tests/golden/query_parser/pharmacy_golden.yaml`
- Contract: `specs/004-semantic-query-parser/contracts/query-understanding.md`
- Validation runbook: `specs/004-semantic-query-parser/quickstart.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create target packages, test scaffolding, and feature flags before any parser logic.

- [x] T001 Create `src/core/query_parser/__init__.py` exporting `semantic_parse_async`, `ParseResult`, `QueryPlan`, `ConversationContext`, `build_conversation_context`
- [x] T002 Add `RAG_SEMANTIC_PARSER_ENABLED` and `RAG_SEMANTIC_PARSER_SHADOW` to `src/helpers/config.py` (`Settings` class + `.env.example` entries)
- [x] T003 [P] Create test package dirs `tests/unit/core/query_parser/__init__.py` and `tests/golden/query_parser/.gitkeep`
- [x] T004 [P] Create golden-set runner scaffold `scripts/run_query_parser_golden.py` (argparse + YAML loader; exit non-zero on threshold miss — implementation stub OK)

**Checkpoint**: Package skeleton and flags exist. No behavior change yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core parser module, field-pack config loading, and plan-driven field resolution. MUST complete before any user-story pipeline integration.

**⚠️ CRITICAL**: No `answer_service.py` integration until this phase is done.

- [x] T005 Add `ParserProfile` and `GroundingConfig` Pydantic models to `src/fields/schemas.py` per `data-model.md`
- [x] T006 [P] Create default `src/fields/generic/parser.yaml` (prompt template, `document_language: en`, timeout, grounding defaults)
- [x] T007 Implement `QueryPlan`, `ConversationContext`, `TurnSummary`, `ParseResult` in `src/core/query_parser/schema.py` with Pydantic validators matching `contracts/query-understanding.md` JSON schema
- [x] T008 [P] Extract pre-parse normalization (Unicode, Arabic diacritics, digit transliteration, whitespace) into `src/core/query_parser/normalize.py` from `src/core/query_understanding.py` — no intent/field/entity regex
- [x] T009 Add `_load_parser()` and `parser_profile` field to `FieldProfile` in `src/services/FieldRegistry.py`; deep-merge `generic.parser` < `domain.parser` < `project.config_json.parser`
- [x] T010 [P] Implement field-registry validation in `src/core/query_parser/validator.py` (`validate_query_plan(plan, field_registry) → QueryPlan`)
- [x] T011 [P] Implement catalog entity grounding in `src/core/query_parser/grounding.py` (fingerprint index reuse from legacy `build_catalog_fingerprint_index`; `ground_entity(plan, catalog_terms, index) → QueryPlan`)
- [x] T012 Implement `build_conversation_context()` in `src/core/query_parser/context.py` per contract (`current_entity` from prior `query_plan` metadata, bounded `recent_turns`)
- [x] T013 Add `resolve_from_plan()` to `src/core/field_resolution.py` mapping `QueryPlan.field` → `FieldResolution` via registry + manifest (keep `resolve_query_field` temporarily for legacy path)
- [x] T014 Implement `semantic_parse_async()` orchestration in `src/core/query_parser/parser.py` (normalize → LLM JSON → validate → ground → `ParseResult`; timeout/retry/degradation per FR-014)
- [x] T015 [P] Unit tests for schema + validator in `tests/unit/core/query_parser/test_schema.py` and `tests/unit/core/query_parser/test_validator.py`
- [x] T016 [P] Unit tests for grounding + normalize in `tests/unit/core/query_parser/test_grounding.py` and `tests/unit/core/query_parser/test_normalize.py`
- [x] T017 [P] Unit tests for parser orchestration with mocked LLM in `tests/unit/core/query_parser/test_parser.py` (include EUTHYROX strengths JSON fixture)

**Checkpoint**: `semantic_parse_async` callable in isolation; all foundational unit tests pass.

---

## Phase 3: User Story 1 — Direct Entity Question in Arabic (Priority: P1) 🎯 MVP

**Goal**: Pharmacist asks `"ايه كل تركيزات يوثيروكس؟"` and system produces correct `QueryPlan` + retrieves EUTHYROX strengths.

**Independent Test**: POST chat with Arabic strengths query (no prior context) → answer cites strength chunks for EUTHYROX; logs show `field=strengths`, `entity=EUTHYROX`.

### Tests for User Story 1

- [x] T018 [P] [US1] Add golden cases `euthyrox_strengths_ar` and `euthyrox_strengths_en` to `tests/golden/query_parser/pharmacy_golden.yaml`
- [x] T019 [P] [US1] Integration test direct Arabic strengths query in `tests/integration/rag/test_semantic_parser_euthyrox_strengths.py`

### Implementation for User Story 1

- [x] T020 [P] [US1] Create `src/fields/pharmacy/parser.yaml` (~40 lines: prompt, `document_language: en`, entity grounding metadata keys from `fields/pharmacy/fields.yaml`)
- [x] T021 [US1] Wire semantic parser into `src/services/rag/answer_service.py` when `RAG_SEMANTIC_PARSER_ENABLED=true`: call `semantic_parse_async`, use `canonical_query` as retrieval text, skip legacy intent/rewrite for this path
- [x] T022 [US1] Pass `query_plan` and `resolve_from_plan()` result into `search_vector_db_collection` in `src/services/rag/rag_service.py` (or NLP search orchestration module)
- [x] T023 [US1] Map `QueryPlan.operation=list` + `scope=all` to exhaustive retrieval limit in `src/services/rag/answer_service.py` (replaces intent-based `wide_retrieval_intents` for semantic path)
- [x] T024 [US1] Apply `query_plan.entity` as `metadata_filter` on entity column in retrieval search path (`src/stores/vectordb/providers/pgvector/search.py` or caller)

**Checkpoint**: US1 end-to-end works with feature flag on. MVP deliverable.

---

## Phase 4: User Story 2 — Follow-up Using Conversation Context (Priority: P1)

**Goal**: Turn 2 `"ايه الادوية المتعارضة معاه؟"` resolves `entity=EUTHYROX` from session without user re-stating the drug.

**Independent Test**: Two-turn chat (establish EUTHYROX → ask interactions follow-up) → correct interactions retrieval.

### Tests for User Story 2

- [x] T025 [P] [US2] Unit tests for context builder in `tests/unit/core/query_parser/test_context.py` (carry-over, ambiguous reference, entity switch)
- [x] T026 [P] [US2] Add golden case `euthyrox_interactions_followup` to `tests/golden/query_parser/pharmacy_golden.yaml`
- [x] T027 [US2] Integration test two-turn follow-up in `tests/integration/rag/test_semantic_parser_followup.py`

### Implementation for User Story 2

- [x] T028 [US2] Persist `query_plan` and `canonical_query` in chat message metadata on each answer turn in `src/services/rag/answer_service.py` (use existing `ChatMessageModel` metadata JSON field or add column per `data-model.md`)
- [x] T029 [US2] Load prior parse metadata when building `ConversationContext` in `src/services/rag/answer_service.py` before `semantic_parse_async`
- [x] T030 [US2] Update parser prompt assembly in `src/core/query_parser/parser.py` to inject `conversation_context` (current_entity + recent turns) per `parser.yaml` `context_turn_window`

**Checkpoint**: US1 and US2 both pass independently.

---

## Phase 5: User Story 3 — Mixed-Language and Colloquial Input (Priority: P2)

**Goal**: Code-switched queries like `"يوثيروكس interactions ايه؟"` parse correctly without separate language pipelines.

**Independent Test**: Golden-set mixed-language cases pass; pre-parse normalization handles Arabic digits/diacritics.

### Tests for User Story 3

- [x] T031 [P] [US3] Add mixed-language golden cases to `tests/golden/query_parser/pharmacy_golden.yaml` (≥5 cases)
- [x] T032 [P] [US3] Extend `tests/unit/core/query_parser/test_normalize.py` with Arabic-digit and diacritic fixtures

### Implementation for User Story 3

- [x] T033 [US3] Verify `normalize.py` is invoked as first step in `src/core/query_parser/parser.py` before LLM call (wire if not already)
- [x] T034 [US3] Add mixed-language examples to prompt in `src/fields/pharmacy/parser.yaml` instructing single-path Arabic/English/mixed handling

**Checkpoint**: US3 golden cases pass. No separate Arabic/English code paths.

---

## Phase 6: User Story 4 — Parser Failure and Clarification (Priority: P2)

**Goal**: Unknown entity or parse failure triggers clarification — never silent wrong retrieval.

**Independent Test**: Query with `XYZUNKNOWN` drug → `needs_clarification=true`, user-facing prompt, no retrieval.

### Tests for User Story 4

- [x] T035 [P] [US4] Unit tests for degradation paths in `tests/unit/core/query_parser/test_parser.py` (timeout, invalid JSON, grounding miss)
- [x] T036 [US4] Integration test unknown-entity clarification in `tests/integration/rag/test_semantic_parser_clarify.py`

### Implementation for User Story 4

- [x] T037 [US4] Implement clarification short-circuit in `src/services/rag/answer_service.py`: when `query_plan.needs_clarification=true`, return `clarification_prompt` without calling retrieval
- [x] T038 [US4] Harden degradation path in `src/core/query_parser/parser.py`: retry once → `field=unknown` fallback → `needs_clarification` (never fabricate grounded entity)
- [x] T039 [US4] Increment `RAG_CLARIFICATION_TOTAL` and log `outcome=clarify` when clarification triggered in `src/services/rag/answer_service.py`

**Checkpoint**: SC-006 satisfied — 100% unknown-entity cases clarify.

---

## Phase 7: User Story 5 — Domain-Agnostic Field Packs (Priority: P3)

**Goal**: Legal/generic projects use same parser architecture with their own field registry.

**Independent Test**: Parser with legal `fields.yaml` concepts produces valid `QueryPlan.field` from allowed registry keys.

### Tests for User Story 5

- [x] T040 [P] [US5] Unit test legal/generic field validation in `tests/unit/core/query_parser/test_validator.py` using fixture registry
- [x] T041 [P] [US5] Add ≥3 legal-domain golden cases to `tests/golden/query_parser/legal_golden.yaml`

### Implementation for User Story 5

- [x] T042 [P] [US5] Create `src/fields/legal/parser.yaml` with legal-appropriate prompt and `document_language`
- [x] T043 [US5] Inject `allowed_fields` from `field_registry.concepts` at profile build time in `src/services/FieldRegistry.py` when `parser.yaml` `allowed_fields` is empty
- [x] T044 [US5] Verify graceful `field=unknown` retrieval (canonical-query-only) for minimal generic pack in `src/services/rag/answer_service.py`

**Checkpoint**: SC-007 satisfied — non-pharmacy parser path works.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Observability, full golden set, legacy removal, feature-flag default flip.

- [x] T045 [P] Add `RAG_PARSE_LATENCY` histogram to `src/utils/metrics.py` (labels: `project_id`, `domain_key`, `outcome`)
- [x] T046 Emit structured `query_parse_complete` log event in `src/core/query_parser/parser.py` (fields per contract)
- [x] T047 Complete golden-set runner logic in `scripts/run_query_parser_golden.py` (≥95% entity+field, ≥90% operation+scope thresholds)
- [x] T048 Populate ≥50 pharmacy cases in `tests/golden/query_parser/pharmacy_golden.yaml` and ≥20 follow-up context cases
- [x] T049 Implement shadow-mode logging in `src/services/rag/answer_service.py` when `RAG_SEMANTIC_PARSER_SHADOW=true` (log new `QueryPlan` alongside legacy path without changing answers)
- [x] T050 Remove legacy query-understanding hot path from `src/services/rag/answer_service.py` (delete calls to `classify_intent_regex`, `rewrite_query_async`, `build_multi_query_variants`, `extract_last_entity`, `resolve_catalog_terms`, follow-up grounding branches)
- [x] T051 Delete `src/core/query_understanding.py` after migrating any still-needed helpers to `src/core/query_parser/`
- [x] T052 Delete `src/fields/pharmacy/query_rewrite.yaml` and remove `QueryRewriteProfile` loading from `src/services/FieldRegistry.py` when semantic parser is default
- [x] T053 [P] Remove dead `intent_config` / `classify_intent` usage from query-understanding path in `src/services/FieldRegistry.py` and `src/fields/pharmacy/compat.py`
- [x] T054 Set `RAG_SEMANTIC_PARSER_ENABLED` default to `true` in `src/helpers/config.py`; remove shadow flag after validation
- [x] T055 Run full quickstart validation per `specs/004-semantic-query-parser/quickstart.md` and document results in `specs/004-semantic-query-parser/quickstart.md` pass-criteria checklist

**Checkpoint**: Legacy pipeline removed; golden set green; quickstart pass criteria met.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — **MVP**
- **US2 (Phase 4)**: Depends on Phase 3 (needs pipeline wire + metadata persistence)
- **US3 (Phase 5)**: Depends on Phase 2; can parallel with US2 after Phase 3
- **US4 (Phase 6)**: Depends on Phase 3 (needs answer_service wire); grounding from Phase 2
- **US5 (Phase 7)**: Depends on Phase 2 validator; can parallel with US3/US4 after Phase 3
- **Polish (Phase 8)**: Depends on US1–US4 minimum; US5 recommended before legacy deletion

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 (P1) | Foundational | Arabic EUTHYROX strengths, no context |
| US2 (P1) | US1 pipeline wire | Two-turn interactions follow-up |
| US3 (P2) | Foundational normalize | Mixed-language golden cases |
| US4 (P2) | US1 pipeline wire | Unknown entity → clarification |
| US5 (P3) | Foundational validator | Legal/generic field pack |

### Within Each User Story

- Tests written first (fail before implementation)
- Config/YAML before service integration
- Core module before `answer_service.py` changes
- Integration test before story checkpoint

### Parallel Opportunities

**Phase 1**: T003 ∥ T004  
**Phase 2**: T006 ∥ T008; T010 ∥ T011 ∥ T012; T015 ∥ T016 ∥ T017  
**Phase 3**: T018 ∥ T019 ∥ T020 (tests + yaml before wire tasks T021–T024 sequential)  
**Phase 4**: T025 ∥ T026 (tests parallel); T028–T030 sequential  
**Phase 5**: T031 ∥ T032 ∥ T034  
**Phase 6**: T035 ∥ T036  
**Phase 7**: T040 ∥ T041 ∥ T042  
**Phase 8**: T045 ∥ T048 ∥ T053  

**Cross-story parallelism** (after Phase 3): Developer A → US2; Developer B → US3 + US5; Developer C → US4

---

## Parallel Example: User Story 1

```bash
# Tests + config in parallel:
T018: tests/golden/query_parser/pharmacy_golden.yaml
T019: tests/integration/rag/test_semantic_parser_euthyrox_strengths.py
T020: src/fields/pharmacy/parser.yaml

# Then sequential integration:
T021 → T022 → T023 → T024: answer_service.py + rag_service.py + search path
```

---

## Parallel Example: Foundational Phase

```bash
# Models + config in parallel:
T006: src/fields/generic/parser.yaml
T008: src/core/query_parser/normalize.py

# Guardrails in parallel:
T010: src/core/query_parser/validator.py
T011: src/core/query_parser/grounding.py
T012: src/core/query_parser/context.py

# Tests in parallel after T014:
T015, T016, T017
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T017)
3. Complete Phase 3: User Story 1 (T018–T024)
4. **STOP and VALIDATE**: Run `pytest tests/integration/rag/test_semantic_parser_euthyrox_strengths.py` + golden cases
5. Demo Arabic strengths query end-to-end

### Incremental Delivery

1. Setup + Foundational → parser module testable in isolation
2. US1 → MVP (direct Arabic/English entity questions)
3. US2 → Multi-turn pharmacy workflows
4. US4 → Safety (clarification before wrong retrieval)
5. US3 + US5 → Mixed language + domain generality
6. Polish → Legacy removal + full golden set

### Suggested MVP Scope

**User Story 1 only** (Phases 1–3): ~24 tasks. Delivers the core architectural shift — single semantic parse producing `QueryPlan` consumed by retrieval.

---

## Notes

- Do NOT add new regex intent rules or expand `query_rewrite.yaml` — extend `parser.yaml` only
- Keep `RAG_SEMANTIC_PARSER_ENABLED=false` until T021 completes; use shadow mode (T049) during US2–US4 validation
- `resolve_query_field()` removed from hot path in T050, not before shadow validation
- Compare operations: parser may emit `operation=compare` before retrieval supports it (spec assumption) — retrieval returns clarification or degrades gracefully until v1.1

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001–T004 (4) | — |
| Foundational | T005–T017 (13) | — |
| US1 MVP | T018–T024 (7) | US1 |
| US2 Follow-up | T025–T030 (6) | US2 |
| US3 Mixed lang | T031–T034 (4) | US3 |
| US4 Clarify | T035–T039 (5) | US4 |
| US5 Domain packs | T040–T044 (5) | US5 |
| Polish | T045–T055 (11) | — |
| **Total** | **55 tasks** | |

**Format validation**: All 55 tasks use `- [ ] [Tnnn] [P?] [USn?] Description with file path` ✅
