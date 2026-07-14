# Tasks: Knowledge Representation

**Input**: Design documents from `specs/008-knowledge-representation/`

**Prerequisites**: plan.md âœ… | spec.md âœ… | research.md âœ… | data-model.md âœ… | contracts/pipeline-contract.md âœ… | quickstart.md âœ…

**Tests**: Required per constitution (Principle VII) â€” unit tests per stage, integration test for end-to-end pipeline run.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to ([US1]â€“[US6])
- Include exact file paths in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module directory skeleton, init files, YAML pack, and error types.

- [X] T001 Create `src/core/knowledge/` directory structure with all subdirectories: `extractors/`, `normalizers/`, `discovery/`, `representation/`
- [X] T002 [P] Create `src/core/knowledge/__init__.py`, `src/core/knowledge/extractors/__init__.py`, `src/core/knowledge/normalizers/__init__.py`, `src/core/knowledge/discovery/__init__.py`, `src/core/knowledge/representation/__init__.py`
- [X] T003 [P] Create `src/core/knowledge/errors.py` with `KnowledgeRepresentationError`, `EvidenceIntegrityError`, `StrategyNotFoundError`, `KnowledgeValidationFailedError` (all inherit from a common base)
- [X] T004 [P] Create `src/fields/generic/knowledge_representation.yaml` with default config: `extractor_strategy: structural`, `normalizer_strategy: rule_based`, `discoverer_strategy: structural`, `representation_strategies: []`, `max_units: null`, `extractor_params: {}`, `normalizer_params: {alias_map: {}}`, `discoverer_params: {}`
- [X] T005 Create `tests/unit/core/knowledge/__init__.py` and `tests/unit/core/knowledge/conftest.py` with fixture ChunkSets: `chunk_set_five_forms`, `chunk_set_alias_pair`, `chunk_set_single_degraded`, `chunk_set_malformed`, `chunk_set_ner_compatible`, `chunk_set_50_chunks`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, strategy interfaces, pipeline skeleton, and registry. These MUST be complete before any user story can be implemented.

**âš ï¸ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Create enumerations in `src/core/knowledge/models.py`: `KnowledgeUnitType`, `KnowledgeRelationshipType`, `KnowledgeValidationStatus`, `ValidationRuleOutcome` (all as `Literal` types per data-model.md Â§0)
- [X] T007 [P] Implement `EvidenceReference` Pydantic model in `src/core/knowledge/models.py` with `frozen=True`: fields `id`, `chunk_ids`, `element_ids`, `document_model_id`, `asset_id`; deterministic `id` via `"er_" + SHA256(canonical_payload)[:16]` (research R2)
- [X] T008 [P] Implement `KnowledgeUnitMetadata` and `KnowledgeRelationshipMetadata` Pydantic models in `src/core/knowledge/models.py` with `frozen=True` (data-model.md Â§3, Â§5)
- [X] T009 Implement `KnowledgeUnit` Pydantic model in `src/core/knowledge/models.py` with `frozen=True`: all fields per data-model.md Â§2; `evidence_references` and `relationships` as `tuple`; deterministic `id` via `"ku_" + SHA256(canonical_payload)[:16]`; validator that `evidence_references` is non-empty
- [X] T010 Implement `KnowledgeRelationship` Pydantic model in `src/core/knowledge/models.py` with `frozen=True`: all fields per data-model.md Â§4; `evidence_references` as `tuple`; deterministic `id` via `"kr_" + SHA256(canonical_payload)[:16]`; validator that `source_unit_id != target_unit_id` and `evidence_references` non-empty
- [X] T011 [P] Implement `RelationshipCandidate` Pydantic model in `src/core/knowledge/models.py` (NOT frozen â€” intermediate entity): fields per data-model.md Â§6; `score: float | None`
- [X] T012 Implement `ValidationRuleResult`, `KnowledgeValidationStatistics`, `KnowledgeValidationMetadata`, `KnowledgeValidationReport` models in `src/core/knowledge/models.py` with `frozen=True`; validator on `KnowledgeValidationReport` that `status` is derived correctly from `errors`/`warnings` counts (data-model.md Â§7â€“Â§10)
- [X] T013 Implement `KnowledgePackageMetadata`, `KnowledgePackageStatistics`, `KnowledgePackage` models in `src/core/knowledge/models.py` with `frozen=True`; `knowledge_units` and `knowledge_relationships` as `tuple`; `evidence_registry` as `dict[str, EvidenceReference]`; `validation_report` always present (data-model.md Â§11â€“Â§13)
- [X] T014 [P] Implement `KnowledgeExtractionConfig` Pydantic model in `src/core/knowledge/models.py` (NOT frozen â€” configuration): all fields per data-model.md Â§14 with defaults matching `knowledge_representation.yaml`
- [X] T015 Create `src/core/knowledge/interfaces.py` with `KnowledgeUnitExtractor` (ABC), `KnowledgeNormalizer` (ABC), `RelationshipDiscoverer` (ABC with `generate_candidates()` and `validate_candidates()` methods), `KnowledgeRepresentationStrategy` (Protocol); all typed per data-model.md Â§15
- [X] T016 [P] Create `src/core/knowledge/registry.py` with four registries (`ExtractorRegistry`, `NormalizerRegistry`, `DiscovererRegistry`, `RepresentationStrategyRegistry`), each exposing `register(strategy_id, impl)` and `get(strategy_id) -> impl` with `StrategyNotFoundError` on missing key
- [X] T017 Create `src/core/knowledge/pipeline.py` with `KnowledgeRepresentationPipeline.__init__()` accepting all four strategy instances plus `KnowledgeValidator` and `KnowledgePackageAssembler`; skeleton `run(chunk_set, config) -> KnowledgePackage` wiring the six-stage sequence in correct order (data-model.md Â§16)

**Checkpoint**: Foundation complete â€” models, interfaces, registry, and pipeline skeleton are in place. User story phases can now begin.

---

## Phase 3: User Story 1 + 3 â€” Semantic Extraction & Full Evidence Traceability (Priority: P1) ðŸŽ¯ MVP

**Goal (US1)**: Any semantic form in a ChunkSet â€” procedure, definition, measurement, table, assertion â€” produces a `KnowledgeUnit` of the correct type with its EvidenceReferences intact.

**Goal (US3)**: Every Knowledge Unit and Knowledge Relationship carries a complete, unbroken 4-level EvidenceReference chain (Chunk â†’ StructuralElement â†’ DocumentModel â†’ asset).

**Independent Test**: Run `pytest tests/unit/core/knowledge/test_structural_extractor.py tests/unit/core/knowledge/test_assembler.py -v` â€” all five semantic-form KUs are produced with correct types and non-empty evidence collections resolving all four traceability levels.

### Tests for US1 + US3

- [X] T018 [P] [US1] Write `tests/unit/core/knowledge/test_structural_extractor.py` with tests: `test_five_forms_correct_types` (SC-001), `test_no_external_calls` (SC-007), `test_ner_strategy_swappability` (SC-009), `test_strategy_swap_zero_core_change` (SC-004) â€” all assertions written, tests expected to fail
- [X] T019 [P] [US3] Write `tests/unit/core/knowledge/test_models.py` with tests: `test_evidence_traceability_all_levels` (SC-002), `test_knowledge_unit_immutability` (SC-011), `test_evidence_reference_id_stability` â€” all assertions written, tests expected to fail

### Implementation for US1 + US3

- [X] T020 [US1] Implement `StructuralKnowledgeUnitExtractor` in `src/core/knowledge/extractors/structural.py`: 9-rule priority chain (procedural pattern â†’ definition pattern â†’ measurement pattern â†’ table â†’ list â†’ code/quote â†’ figure-placeholder â†’ heading â†’ default fallback); `strategy_id = "structural"`; `extract(chunk_set, config) -> list[KnowledgeUnit]`; produces exactly one KU per Chunk with `semantic_content` typed per research R8 (dict shape per KU type) and `"source_surface_form"` in `attributes`
- [X] T021 [US1] Implement `EvidenceReference` construction helper in `src/core/knowledge/extractors/structural.py`: given a `Chunk`, construct `EvidenceReference` with `chunk_ids=[chunk.identity.chunk_id]`, `element_ids=chunk.identity.source_element_ids`, `document_model_id=chunk.identity.document_id`, `asset_id=chunk_set.asset_id`; verify all four levels are non-empty before construction
- [X] T022 [US1] Implement `KnowledgePackageAssembler` in `src/core/knowledge/assembly.py`: `assemble(units, relationships, config, chunk_set) -> KnowledgePackage`; builds `evidence_registry` as union of all EvidenceReferences from all KUs and KRs keyed by `er.id`; computes `KnowledgePackageMetadata` (package_id via SHA256, strategy ids, config_hash, timestamps); computes `KnowledgePackageStatistics` (unit counts by type, relationship counts by type, coverage pct)
- [X] T023 [US3] Add `field_validator` on `KnowledgeUnit.evidence_references` enforcing non-empty and each `EvidenceReference` has all four non-empty traceability levels (`chunk_ids`, `element_ids`, `document_model_id`, `asset_id`) â€” validator raises `EvidenceIntegrityError` on violation
- [X] T024 [US3] Add `field_validator` on `KnowledgeRelationship.evidence_references` with same 4-level enforcement as T023
- [X] T025 [US1] Wire `StructuralKnowledgeUnitExtractor` into `ExtractorRegistry` with id `"structural"` in `src/core/knowledge/registry.py`; add factory function `build_pipeline_from_config(config, registries) -> KnowledgeRepresentationPipeline` in `src/core/knowledge/pipeline.py`
- [X] T026 [US1] Add structured logging in `src/core/knowledge/extractors/structural.py` at extraction boundary: log `asset_id`, `chunk_count`, `ku_count_by_type`, `extractor_strategy_id` (NFR-007)

**Checkpoint**: US1 + US3 complete â€” `chunk_set_five_forms` produces 5 KUs of correct types, every KU's evidence chain resolves all 4 levels, immutability enforced by frozen models.

---

## Phase 4: User Story 2 â€” Strategy-Based Pipeline, Zero Core Change on Swap (Priority: P1)

**Goal**: A new extractor, normalizer, or discoverer strategy can be registered and activated via configuration with zero changes to core pipeline dispatch logic or the `KnowledgePackage` model.

**Independent Test**: Run `pytest tests/unit/core/knowledge/test_structural_extractor.py::test_strategy_swap_zero_core_change -v` â€” registering a stub extractor and switching `config.extractor_strategy` routes to it without any `if/else` in core.

### Tests for US2

- [X] T027 [P] [US2] Write `tests/unit/core/knowledge/test_registry.py` with tests: `test_extractor_registry_dispatch`, `test_unknown_strategy_raises`, `test_pipeline_uses_config_strategy` â€” all assertions written, tests expected to fail

### Implementation for US2

- [X] T028 [US2] Implement `KnowledgeExtractionConfig` loading from pack YAML in `src/core/knowledge/pipeline.py`: load `src/fields/{domain}/knowledge_representation.yaml` following generic < domain < project precedence (`src/core/field_resolution.py` pattern); merge into `KnowledgeExtractionConfig`
- [X] T029 [US2] Add `build_pipeline_from_config(config: KnowledgeExtractionConfig) -> KnowledgeRepresentationPipeline` factory in `src/core/knowledge/pipeline.py` that calls `ExtractorRegistry.get(config.extractor_strategy)`, `NormalizerRegistry.get(config.normalizer_strategy)`, `DiscovererRegistry.get(config.discoverer_strategy)` â€” no `if/else` on strategy name, pure registry dispatch
- [X] T030 [P] [US2] Implement `StubPassthroughNormalizer` in `src/core/knowledge/normalizers/__init__.py` (identity normalizer for testing â€” returns input unchanged) and register with id `"passthrough"` in `NormalizerRegistry`; implement `StubNoOpDiscoverer` in `src/core/knowledge/discovery/__init__.py` (returns empty candidates/relationships) and register with id `"noop"` in `DiscovererRegistry`
- [X] T031 [US2] Write `tests/unit/core/knowledge/test_structural_extractor.py::test_strategy_swap_zero_core_change` fixture: register `StubAlternativeExtractor` (produces all `assertion`-typed KUs), switch `config.extractor_strategy = "stub_alternative"`, run pipeline, verify package shape unchanged and zero diffs in core dispatch code

**Checkpoint**: US2 complete â€” strategy swap is configuration-only, no core changes required; registry dispatches correctly.

---

## Phase 5: User Story 4 â€” Knowledge Normalization (Priority: P2)

**Goal**: Two raw KUs representing the same concept under different surface forms are merged into one canonical KU whose `evidence_references` contains references from both source chunks, before Relationship Discovery runs.

**Independent Test**: Run `pytest tests/unit/core/knowledge/test_rule_based_normalizer.py -v` â€” alias deduplication produces exactly one canonical KU from `chunk_set_alias_pair`, evidence from both chunks preserved.

### Tests for US4

- [X] T032 [P] [US4] Write `tests/unit/core/knowledge/test_rule_based_normalizer.py` with tests: `test_alias_deduplication` (SC-010), `test_exact_match_deduplication`, `test_normalization_preserves_all_evidence`, `test_normalization_does_not_create_relationships`, `test_normalization_is_deterministic` (SC-003 partial) â€” all assertions written, tests expected to fail

### Implementation for US4

- [X] T033 [US4] Implement `RuleBasedKnowledgeNormalizer` in `src/core/knowledge/normalizers/rule_based.py`: three-pass normalization per research R4: (1) surface normalization (lowercase + strip + collapse whitespace); (2) alias resolution from `config.normalizer_params["alias_map"]` dict; (3) exact-match deduplication â€” group by normalized key, merge evidence_references as union, keep first KU in group as canonical, set `metadata.normalization_status = "merged"` on canonical and exclude merged duplicates from output; `strategy_id = "rule_based"`
- [X] T034 [US4] Implement `RelationshipCandidateValidator` in `src/core/knowledge/discovery/validator.py`: `validate(candidates, units) -> list[KnowledgeRelationship]`; filters: dangling `source_unit_id`/`target_unit_id` (not in unit id set) â†’ drop + log; self-referencing (source == target) â†’ drop; `sequence` cycles â†’ drop; surviving candidates converted to `KnowledgeRelationship` (research R5 sub-stage 2)
- [X] T035 [US4] Implement `StructuralRelationshipDiscoverer` in `src/core/knowledge/discovery/structural.py`: `generate_candidates()` produces three candidate types per research R5: (a) `sequence` for adjacent KUs (iâ†’i+1 in normalized list), (b) `containment` from `chunk.relationships.parent_chunk_id` mapping, (c) `elaboration` for KUs sharing the same `heading_path` prefix (first KU in group as source); `validate_candidates()` delegates to `RelationshipCandidateValidator`; `strategy_id = "structural"`
- [X] T036 [US4] Register `RuleBasedKnowledgeNormalizer` with id `"rule_based"` in `NormalizerRegistry`; register `StructuralRelationshipDiscoverer` with id `"structural"` in `DiscovererRegistry` in `src/core/knowledge/registry.py`
- [X] T037 [US4] Add structured logging in `src/core/knowledge/normalizers/rule_based.py`: log `merged_count`, `alias_resolutions`, `dedup_count`, `normalizer_strategy_id`; add structured logging in `src/core/knowledge/discovery/structural.py`: log `candidate_count`, `validated_relationship_count`, `dropped_dangling_count`, `discoverer_strategy_id` (NFR-007)

**Checkpoint**: US4 complete â€” normalization deduplicates by surface form, alias resolution works from pack YAML, evidence always preserved, discoverer produces structural relationships.

---

## Phase 6: User Story 6 â€” Knowledge Validation Gates (Priority: P3)

**Goal**: Every assembled Knowledge Package is validated against all named quality rules; any violation is surfaced as a named entry in the `KnowledgeValidationReport` with zero violations silently passing through.

**Independent Test**: Run `pytest tests/unit/core/knowledge/test_validator.py -v` â€” malformed inputs (no EvidenceReference, dangling KR, unrecognized type) are all caught in the report; package returned without silent violations.

### Tests for US6

- [X] T038 [P] [US6] Write `tests/unit/core/knowledge/test_validator.py` with tests: `test_malformed_inputs_caught` (SC-005), `test_validation_report_always_present`, `test_passed_status_on_clean_package`, `test_warning_on_max_unit_exceeded`, `test_report_immutable_after_production` â€” all assertions written, tests expected to fail

### Implementation for US6

- [X] T039 [US6] Implement `KnowledgeValidator` in `src/core/knowledge/validation.py`: `validate(draft_package, chunk_set, document_model_id) -> KnowledgeValidationReport`; applies all seven named quality rules (data-model.md Â§7): `evidence_non_empty`, `reference_resolution`, `dangling_unit_reference`, `recognized_unit_type`, `full_traceability_chain`, `max_unit_count_exceeded` (warning), `unit_without_semantic_content` (warning)
- [X] T040 [US6] Implement each named quality rule as a private method in `KnowledgeValidator`: each rule returns `ValidationRuleResult`; error rules filter violating entities from the final package (or mark for exclusion); warning rules add to report without exclusion; all rules produce named `ValidationRuleResult` with `implicated_unit_ids`/`implicated_relationship_ids`
- [X] T041 [US6] Wire `KnowledgeValidator.validate()` into `KnowledgeRepresentationPipeline.run()` as stage 6 in `src/core/knowledge/pipeline.py`: pass draft package â†’ validator â†’ get report â†’ construct final `KnowledgePackage` with `validation_report` embedded; raise `KnowledgeValidationFailedError` only when `config` specifies `fail_on_error = true` (default: return package with report regardless)
- [X] T042 [US6] Implement `tests/unit/core/knowledge/test_validator.py::test_malformed_inputs_caught` using `model_construct` to bypass Pydantic validation for injecting violations: (1) KU with empty `evidence_references` tuple, (2) KR with `source_unit_id = "ku_ghost"` not in package, (3) KU with `type = "alien_type"` (force-set via `model_construct`); verify all three appear in `report.errors`

**Checkpoint**: US6 complete â€” all named quality rules enforced; validation report always present and structurally complete; malformed inputs cannot silently enter the final package.

---

## Phase 7: User Story 5 â€” Knowledge Graph as Optional Representation (Priority: P3)

**Goal**: A `KnowledgeRepresentationStrategy` can be applied to a `KnowledgePackage` to generate a specific representation format; the package is provably unchanged before and after application; Knowledge Graph is one optional strategy, not the primary output.

**Independent Test**: Run `pytest tests/unit/core/knowledge/test_assembler.py::test_representation_strategy_no_mutation -v` â€” two stub strategies applied sequentially to same package; package identical before and after both; two different output formats produced.

### Tests for US5

- [X] T043 [P] [US5] Write `tests/unit/core/knowledge/test_assembler.py` with tests: `test_representation_strategy_no_mutation` (SC-006), `test_idempotent_reprocessing` (SC-003), `test_no_graph_generated_when_not_configured` â€” all assertions written, tests expected to fail

### Implementation for US5

- [X] T044 [US5] Implement `KnowledgeRepresentationStrategy` re-export and `NoOpRepresentationStrategy` (returns `None`) in `src/core/knowledge/representation/base.py`; implement `StubGraphRepresentationStrategy` (returns `{"nodes": [...], "edges": [...]}` from KUs and KRs) and `StubRelationalRepresentationStrategy` (returns `list[dict]`) for testing and as reference implementations
- [X] T045 [US5] Register `StubGraphRepresentationStrategy` with id `"stub_graph"` and `StubRelationalRepresentationStrategy` with id `"stub_relational"` in `RepresentationStrategyRegistry` in `src/core/knowledge/registry.py`
- [X] T046 [US5] Wire representation strategy application into `KnowledgeRepresentationPipeline.run()` in `src/core/knowledge/pipeline.py`: after stage 6 (validation), iterate `config.representation_strategies` list, call `strategy.apply(final_package)` for each; return `final_package` unchanged; representation artifacts are available via side-channel (returned as optional second value or via callback) â€” package is never replaced or modified (FR-028)
- [X] T047 [US5] Write package equality check utility `assert_package_unchanged(before, after)` in `tests/unit/core/knowledge/conftest.py`: compare `before.metadata.package_id`, `len(before.knowledge_units)`, `len(before.knowledge_relationships)`, `set(before.evidence_registry.keys())` â€” used in SC-006 test

**Checkpoint**: US5 complete â€” KG is one optional read-only projection; package provably unchanged after strategy application; configuring zero strategies produces a valid KP without any graph artifact.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Celery task integration, repository persistence, end-to-end integration test, YAML pack wiring, and benchmarking.

- [X] T048 [P] Create `src/tasks/knowledge_representation.py` with Celery task `run_knowledge_representation(asset_id: str, domain: str, project_id: str) -> str`: load `ChunkSet` from `ChunkRepository`, load `KnowledgeExtractionConfig` from field pack YAML, build pipeline via `build_pipeline_from_config()`, run pipeline, persist result via `KnowledgePackageRepository`, emit structured log with counts and strategy ids; return `package_id`
- [X] T049 [P] Create `src/repositories/knowledge_repository.py` with `KnowledgePackageRepository`: `save(package: KnowledgePackage) -> None` (serialize to JSON via `model_dump(mode="json")`, upsert to `knowledge_packages` table keyed by `(asset_id, extractor_strategy_id)`); `get_by_asset(asset_id: str) -> KnowledgePackage | None` (deserialize via `model_validate`); follow `repositories/base.py` pattern
- [X] T050 Write `tests/integration/test_knowledge_pipeline_e2e.py`: full `chunk_set_five_forms` â†’ `KnowledgeRepresentationPipeline.run()` â†’ verify SC-001, SC-002, SC-003, SC-004, SC-007 in one end-to-end run; assert `validation_report.status` in `{"passed", "passed_with_warnings"}`; assert evidence_coverage_pct > 0; (latency assertion guarded by `--benchmark` flag against 2Ã— chunking baseline)
- [X] T051 [P] Add `src/fields/pharmacy/knowledge_representation.yaml` with pharmacy-specific override: `normalizer_params.alias_map` containing at least one sample pharmaceutical alias pair (e.g., `"asa": "acetylsalicylic acid"`) as a documented example for domain pack extension
- [X] T052 [P] Add `src/fields/legal/knowledge_representation.yaml` with legal domain override: `normalizer_params.alias_map: {}` (empty â€” placeholder for future domain aliases)
- [X] T053 Run `pytest tests/unit/core/knowledge/ -v` and fix any linter errors / failing assertions discovered during integration; run `ruff check src/core/knowledge/` and resolve all warnings

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies â€” start immediately
- **Foundation (Phase 2)**: Depends on Phase 1 â€” **BLOCKS all user story phases**
- **US1 + US3 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 2 + Phase 3 (requires working extractor to test swap)
- **US4 (Phase 5)**: Depends on Phase 2 + Phase 3 (normalizer feeds existing KU list)
- **US6 (Phase 6)**: Depends on Phase 2 + Phase 3 + Phase 4 + Phase 5 (validator receives assembled package)
- **US5 (Phase 7)**: Depends on Phase 2 + Phase 3 + Phase 6 (representation strategies receive validated package)
- **Polish (Phase 8)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 + US3 (P1)**: Can start after Foundation â€” primary deliverable, no story dependencies
- **US2 (P1)**: Can start in parallel with US1+US3 after Foundation â€” registry/factory layer is independent; integration with US1+US3 needed only for swap test
- **US4 (P2)**: Depends on US1+US3 (normalization input = extracted KUs)
- **US6 (P3)**: Depends on US4 (validation runs on assembled package after normalization)
- **US5 (P3)**: Can run in parallel with US6 after Foundation + US1+US3 (representation is read-only; validation is independent)

### Within Each Phase

- Write tests FIRST and ensure they FAIL before implementation
- Models before services (Foundation before user story phases)
- Extractor before assembler (T020 before T022)
- Assembler before validator (T022 before T039)
- Normalizer and discoverer before Celery task (T033â€“T036 before T048)

### Parallel Opportunities

- T002, T003, T004 (Phase 1): All parallel
- T007, T008, T011, T014 (Phase 2): Parallel within foundation once T006 enums exist
- T018, T019 (Phase 3): Test files parallel before implementation
- T020, T021 (Phase 3): Parallel (different concerns in same file)
- T027, T030 (Phase 4): Parallel
- T032 (Phase 5): Parallel with foundation tasks
- T038 (Phase 6): Parallel
- T043 (Phase 7): Parallel
- T048, T049, T051, T052 (Phase 8): All parallel

---

## Parallel Example: User Story 1 + 3

```
# Launch these together after Foundation (Phase 2) complete:
Task T018: Write test_structural_extractor.py (all test bodies, expect fail)
Task T019: Write test_models.py (all test bodies, expect fail)

# Then launch implementation together (T020, T021 are independent):
Task T020: Implement StructuralKnowledgeUnitExtractor (extraction + type mapping)
Task T021: Implement EvidenceReference construction helper (4-level chain)

# Sequentially after T020 + T021:
Task T022: Implement KnowledgePackageAssembler
Task T023: Add evidence_references validator on KnowledgeUnit
Task T024: Add evidence_references validator on KnowledgeRelationship
Task T025: Wire extractor into registry + factory
Task T026: Add structured logging
```

---

## Implementation Strategy

### MVP First (US1 + US3 Only â€” Phases 1â€“3)

1. Complete Phase 1: Setup (T001â€“T005)
2. Complete Phase 2: Foundation (T006â€“T017) â€” **CRITICAL, blocks everything**
3. Complete Phase 3: US1 + US3 (T018â€“T026)
4. **STOP AND VALIDATE**: `pytest tests/unit/core/knowledge/test_structural_extractor.py tests/unit/core/knowledge/test_models.py -v`
5. ChunkSet â†’ KnowledgePackage with correct types + full evidence chain â€” MVP complete

### Incremental Delivery

1. Phases 1â€“3 â†’ MVP: extraction + evidence traceability âœ…
2. Phase 4 â†’ US2: strategy swap confirmed (no core changes)
3. Phase 5 â†’ US4: normalization + relationship discovery
4. Phase 6 â†’ US6: validation gates enforce quality
5. Phase 7 â†’ US5: representation strategies (KG as optional)
6. Phase 8 â†’ Polish: Celery task + repository + e2e integration test

### Parallel Team Strategy

With multiple developers after Foundation (Phase 2):
- Developer A: Phase 3 (US1 + US3) â€” extraction + evidence
- Developer B: Phase 4 (US2) â€” strategy registry + factory
- Developer A+B together: Phase 5 (US4) â€” normalization + discovery
- Developer A: Phase 6 (US6) â€” validation
- Developer B: Phase 7 (US5) â€” representation strategies
- Both: Phase 8 â€” polish

---

## Notes

- `[P]` tasks target different files and have no dependency on incomplete tasks in same phase
- Each user story phase produces an independently runnable `pytest` command
- `frozen=True` on all published models â€” do not use `model_copy(update=...)` without creating a new `id`
- `RelationshipCandidate` is intentionally NOT frozen â€” intermediate entity discarded after validation
- `StubPassthroughNormalizer` and `StubNoOpDiscoverer` (T030) serve as integration test scaffolding until real implementations land in Phase 5
- The Celery task (T048) MUST be async-compatible and MUST NOT block HTTP request handlers (Constitution X)
- All `strategy_id` values MUST match the corresponding registry key exactly â€” no magic strings in `pipeline.py`
- Avoid committing `knowledge_packages` migration until `KnowledgePackageRepository` (T049) is complete
