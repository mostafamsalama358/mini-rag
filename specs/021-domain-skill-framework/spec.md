# Feature Specification: Domain Skill Framework for RAG

**Feature Branch**: `021-domain-skill-framework`

**Created**: 2026-07-26

**Updated**: 2026-07-26

**Status**: Draft

**Input**: User description: "Introduce Domain Skills as a first-class RAG concept. Each domain owns its Skills. User must explicitly choose a Skill before asking; no automatic intent/skill/alias detection. Skills drive retrieval profile, metadata filters (via Metadata Profiles), strategy, prompt, validation, and output formatting. Query parser extracts entities only. Domains remain plugins; engine stays domain-agnostic."

---

## Summary

This feature introduces **Domain Skills** as the deterministic entry point for domain-specific question answering. A Skill is a complete, named retrieval capability owned by a Domain Pack (e.g. Pharmacy Interactions, Dosage, Pregnancy). The chat UI presents Skills as selectable controls; the user’s selection is the sole authority for which capability runs.

Skills are **not** prompts, aliases, intent labels, or classifier outputs. Each Skill binds a retrieval capability through a **Metadata Profile** (filters and retrieval targeting), plus validation, prompt/template selection, and output formatting policy—without embedding metadata schema details inside the Skill itself.

**Primary outcomes**: deterministic retrieval, simpler query parsing (entity extraction only), stronger metadata filtering, higher precision, lower latency, and modular multi-domain architecture.

**Architecture stance (normative)**: Domain Skills are a **Domain Pack capability** on the existing sole Answer + Retrieval path (016). This feature does **not** create a Recommendation Service, Skill microservice, parallel answer path, or new sole owner. Engine code remains domain-agnostic and loads Domain → Skills → Metadata Profiles → Retriever bindings at runtime.

---

## Relationship to Existing Features

| Feature | Relationship |
|---------|----------------|
| **016 Architecture Consolidation** | Binding. Skills extend Domain Pack behavior on the sole Answer/Retrieval path. No new sole owner for “Skill Execution.” No parallel production skill pipeline. Exception ADR required if a dedicated Skill owner is later proposed. |
| **002 Field Registry / Domain Packs** | Skills and Metadata Profiles are Domain Pack extension points. Each domain owns its Skill registry and profile set; the engine loads packs without pharmacy-/legal-specific hardcoding. |
| **004 Semantic Query Parser** | When a Skill is selected, Query Understanding **MUST NOT** predict intent, skill, or field-from-language for capability routing. Parser responsibility narrows to entity (and related slot) extraction under the Skill’s validation rules. Free-form intent classification for skill selection is out of scope and forbidden. |
| **009 Retrieval Planner / 010 Retrieval Engine** | Planner and Engine consume Skill-bound Metadata Profile filters and retrieval strategy constraints. They MUST NOT re-infer skill/intent from raw query text when a Skill is already selected. |
| **011 / 012 / 013** | Evidence, context, and answer composition remain on the sole path; Skill selects prompt/template and output-formatting policy consumed by Answer Generation. |
| **015 Unified Pipeline Migration** | Frozen external `/answer` response field-level contract remains. Skill selection is an **additive request** concern (client supplies selected Skill). Response shape MUST NOT break frozen fields without a separate API contract change. |
| **018 RAG Quality Architecture** | Skill-scoped answers MUST still satisfy grounding, evidence/context quality, and Quality Context/Trace expectations. Skill identity and profile id are quality-trace attributes. |
| **019 RAG Evaluation Framework** | Offline/online eval profiles MAY be skill-scoped (per-skill golden sets and gates). Evaluation remains offline/online/monitoring architecture—not a production stage. |
| **020 Pharmacy Recommendation** | Need-based recommendation remains a pharmacy Domain Pack capability. Under Skills, recommend-mode is invoked only via an explicitly selected Skill (e.g. Alternatives / Consultations)—**not** via automatic recommend-intent detection. Ranking/safety/explanation policies from 020 still apply inside that Skill. |

**Non-goals (explicit):**

- No automatic Intent Classification, Skill Classification, Alias Resolution, Command Detection, or Semantic Routing to choose a Skill.
- No requirement that users type `/Interactions` or similar slash commands; UI (or equivalent client) supplies the Skill.
- No embedding of metadata filter lists inside Skill definitions (filters live in Metadata Profiles).
- No new parallel production retrieval or answer path.
- No new sole owner named “Skill Service.”
- No change to how chunks store metadata at index time (Skill layer only chooses which filters retrieval uses).
- No redesign of ingest/chunking ownership (006 / 017 remain orthogonal).

---

## Design Principles

1. **Skill = retrieval capability** — A Skill fully specifies how a class of questions is retrieved and answered for a domain; it is not a synonym list or intent enum value.
2. **UI selection is source of truth** — The selected Skill id is authoritative for the request. Downstream stages MUST NOT override it by re-classifying the query.
3. **No skill detection** — The platform MUST NOT infer, guess, or remap Skills from free text.
4. **Profiles decouple schema** — Skills reference Metadata Profiles; profiles own filter definitions so metadata schema can evolve without rewriting Skills.
5. **Parser extracts entities only** — Under an explicit Skill, the parser does not predict “what the user wants”; the Skill already defines that.
6. **Domain independence** — The engine knows Domain Pack contracts, not pharmacy/legal/finance specifics. New domains are pack plugins.
7. **Sole path (016)** — Skills constrain and configure the existing pipeline; they do not fork it.

---

## Canonical Skill Pipeline

Logical flow when a Skill is selected (composes existing sole-path stages; not a new deployable pipeline):

```
User
  ↓
Selected Skill (UI / client — source of truth)
  ↓
Query Parser (entity / slot extraction only)
  ↓
Skill Registry (resolve Skill → capability binding)
  ↓
Metadata Profile (filters + retrieval targeting)
  ↓
Retriever (profile-constrained search)
  ↓
Reranker
  ↓
LLM / Answer Generation (Skill prompt + output policy)
```

**Normative clarifications:**

- “Skill Registry” and “Metadata Profile” are Domain Pack resolution steps, not new production owners.
- Planner responsibilities that remain (e.g. composing hybrid/dense/sparse within profile constraints) MUST honor the Skill-selected profile and MUST NOT re-derive capability from text.
- Absent Skill selection in a domain that requires Skills: the system MUST refuse or prompt for Skill selection—never silently classify.

---

## Scope

### In Scope

- First-class Domain Skill concept and per-domain Skill registry
- Explicit Skill selection UX (skill buttons / equivalent client controls) before questioning
- Metadata Profiles referenced by Skills; profile-driven retrieval filters
- Query Understanding narrowed to entity/slot extraction under selected Skill
- Skill-controlled validation rules, prompt/template binding, and output formatting policy
- Pharmacy Skill catalog for the initial domain (listed below)
- Domain-agnostic engine loading of Domain → Skills → Profiles
- Compatibility with 016 sole-path, 015 additive request contract, 018/019 quality and eval surfaces
- Mapping of 020 recommend capability onto explicitly selected Skills (no auto-detect)

### Out of Scope

- Automatic skill/intent/alias/command routing of any kind
- Implementation code, class diagrams, provider selection, or sprint breakdown (planning phase)
- Redesign of chunk storage metadata schema (profiles consume existing/ evolving metadata; ingest ownership unchanged)
- Full Legal/Finance Skill catalogs beyond proving the pack model (stubs/examples allowed in planning)
- Replacing hybrid retrieval or reranking as platform capabilities (Skills constrain targets; they do not remove hybrid/rerank standards from the constitution)
- Breaking changes to frozen `/answer` response fields

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pharmacist selects Interactions then asks about two drugs (Priority: P1)

A pharmacist opens chat for a pharmacy project, sees Skill buttons (Consultations, Interactions, Dosage, …), taps **Interactions**, then types `Panadol with Brufen`. The system treats the request as the Interactions Skill with that query text, extracts the two medicines, retrieves only interaction-relevant material, and answers with interaction-focused grounding.

**Why this priority**: This is the core UX and architecture proof—explicit Skill + entity-only parse + profile-filtered retrieval.

**Independent Test**: With pharmacy Skills enabled, select Interactions and submit `Panadol with Brufen`. Verify Skill id is Interactions (not inferred), entities include both medicines, retrieval is constrained to the Interactions Metadata Profile, and no intent classifier runs for skill choice.

**Acceptance Scenarios**:

1. **Given** a pharmacy project with an Interactions Skill, **When** the user selects Interactions and asks `Panadol with Brufen`, **Then** the request is processed as Skill=Interactions with Query=`Panadol with Brufen`, and the parser extracts medicines Panadol and Brufen without assigning `intent=interaction` via classification.
2. **Given** the same query text submitted under Skill=Dosage instead, **When** the request runs, **Then** retrieval uses the Dosage Metadata Profile (not Interactions), even though the text mentions two drug names.
3. **Given** Interactions is selected, **When** the answer is produced, **Then** citations and content are scoped to interaction-relevant evidence; the system does not require the user to type `/Interactions`.

---

### User Story 2 - User must choose a Skill before asking (Priority: P1)

A user opens chat and tries to type a question without selecting a Skill. The UI prevents submission (or the API rejects the request) and prompts them to choose a Skill first.

**Why this priority**: Determinism depends on mandatory explicit selection; silent fallback to classifiers would reintroduce non-determinism.

**Independent Test**: Attempt answer without Skill on a Skills-enabled domain; verify rejection/prompt and that no classifier assigns a Skill.

**Acceptance Scenarios**:

1. **Given** a domain with a non-empty Skill registry, **When** a question is submitted without a Skill, **Then** the system does not answer via inferred skill and instead requires Skill selection.
2. **Given** Skill buttons are shown, **When** the user selects Dosage then types a question, **Then** that Skill remains bound for the request (and subsequent turns until the user changes Skill, per Assumptions).

---

### User Story 3 - Metadata Profile improves precision without rewriting Skills (Priority: P1)

A pack maintainer expands the `drug_interactions` Metadata Profile to also include warnings and precautions fields. The Interactions Skill still references the same profile name; no Skill definition change is required for the broader filter set to apply.

**Why this priority**: Decoupling Skills from metadata schema is a stated architectural goal.

**Independent Test**: Change only the Metadata Profile filters; re-run Interactions queries; verify filter set updates without Skill file/identity changes.

**Acceptance Scenarios**:

1. **Given** Interactions references profile `drug_interactions`, **When** that profile’s field filters expand from `{interactions}` to `{interactions, warnings, precautions, contraindications}`, **Then** retrieval uses the expanded set without renaming or editing the Skill’s capability identity.
2. **Given** two Skills that share one Metadata Profile, **When** the profile changes, **Then** both Skills observe the updated filters.

---

### User Story 4 - Query parser extracts entities only under a Skill (Priority: P1)

Under Skill=Pregnancy, the user asks `Is Glucophage safe?`. The parser extracts the medicine entity; pregnancy capability comes from the Skill, not from detecting the word “safe” or “pregnancy” in free text for routing.

**Why this priority**: Removes dual maintenance of intent patterns vs Skills and simplifies multilingual parsing.

**Independent Test**: Same surface question under Pregnancy vs Side Effects yields different Skills/profiles; parser entity output is comparable; no skill classifier is invoked.

**Acceptance Scenarios**:

1. **Given** Skill=Pregnancy and query `Is Glucophage safe?`, **When** parsing completes, **Then** entities include Glucophage and capability/routing is Pregnancy from the Skill—not from intent classification.
2. **Given** Skill=Interactions with validation requiring at least one medicine, **When** the user asks `what about food?` with no medicine entity, **Then** validation fails with a clear clarification (e.g. ask for medicine names) rather than guessing another Skill.

---

### User Story 5 - Domain pack author adds Skills without engine changes (Priority: P2)

A maintainer adds Legal Skills (e.g. Clause Lookup, Obligations) and Legal Metadata Profiles inside the legal Domain Pack. A legal project shows those Skill buttons. No pharmacy-specific engine changes are required.

**Why this priority**: Proves domain plugin architecture.

**Independent Test**: Register a second domain Skill registry; assign a project to that domain; verify UI/API lists that domain’s Skills only and retrieval uses that domain’s profiles.

**Acceptance Scenarios**:

1. **Given** domain=legal with its own Skill registry, **When** a user opens chat for a legal project, **Then** Skill controls list legal Skills—not pharmacy Skills.
2. **Given** an unknown Skill id for the project’s domain, **When** a client submits it, **Then** the request is rejected with a clear error (no fuzzy remap to another Skill).

---

### User Story 6 - Recommend capability only via explicit Skill (Priority: P2)

A pharmacist wants need-based alternatives (020). They select the **Alternatives** (or equivalent recommend) Skill, then ask `something for migraine`. Recommendation ranking and safety policies apply because the Skill selected that capability—not because a classifier set `recommend_mode=true`.

**Why this priority**: Preserves 020 value while eliminating automatic recommend-intent detection.

**Independent Test**: Submit a need-based question under Alternatives Skill vs under Leaflet Skill; only Alternatives exercises recommend ranking/safety policy path.

**Acceptance Scenarios**:

1. **Given** Skill=Alternatives, **When** the user asks a need-based question, **Then** recommendation policies (020) apply under the sole answer path.
2. **Given** the same need-based text under Skill=Leaflet, **When** the request runs, **Then** the system does not auto-switch to recommend mode.

---

### Edge Cases

- User changes Skill mid-conversation: the new Skill applies to the next question; prior Skill MUST NOT silently continue if the UI cleared selection.
- Skill requires multiple entities (e.g. Interactions) but only one is provided: validation asks for the missing entity; system MUST NOT invent a second drug.
- Skill selected but query empty: reject with a clear message.
- Metadata Profile references unknown/unindexed fields: retrieval degrades safely (empty or reduced candidates) with observable quality-trace signals; MUST NOT invent evidence.
- Domain has zero Skills configured: project behaves per Assumptions (Skills not required / generic fallback)—documented and consistent.
- Client sends a Skill id from another domain: reject; no cross-domain aliasing.
- Multilingual entity names under a Skill: entity extraction and grounding still apply; Skill routing remains explicit.
- Profile filters match no chunks: return a grounded no-evidence / insufficient-evidence outcome rather than unconstrained corpus search (unless the Skill’s profile explicitly allows broader fallback—default is no silent broadening).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST treat Domain Skills as first-class, named retrieval capabilities owned by each Domain Pack.
- **FR-002**: For domains with a non-empty Skill registry, users MUST explicitly select a Skill before a question is accepted for answering.
- **FR-003**: Chat (or equivalent client) MUST present available Skills as selectable controls (e.g. buttons). Users MUST NOT be required to type slash-commands or skill names for selection.
- **FR-004**: The selected Skill id supplied by the client MUST be the sole authority for capability routing for that request.
- **FR-005**: System MUST NOT perform Intent Classification, Skill Classification, Alias Resolution, Command Detection, or Semantic Routing to choose or replace the Skill.
- **FR-006**: Each Skill MUST declare: stable name/id, Metadata Profile reference, prompt/template binding, validation rules, and output formatting policy (and MAY declare retrieval strategy constraints).
- **FR-007**: Skills MUST NOT embed metadata filter lists directly; filters MUST live in Metadata Profiles referenced by Skills.
- **FR-008**: Metadata Profiles MUST define retrieval filters (e.g. field/source constraints) consumed by the Retriever.
- **FR-009**: Multiple Skills MAY share one Metadata Profile; changing a profile MUST NOT require Skill identity changes.
- **FR-010**: Under a selected Skill, Query Understanding MUST extract entities/slots required by that Skill and MUST NOT predict user intent for capability selection.
- **FR-011**: Retriever MUST apply Metadata Profile filters so search targets skill-relevant chunks rather than the full unconstrained field set (unless the profile intentionally allows broader scope).
- **FR-012**: Indexing/chunk metadata storage MUST remain unchanged by the Skill layer; Skills only select which filters retrieval uses.
- **FR-013**: Engine/core MUST load Domain → Skills → Profiles without hard-coded pharmacy (or other vertical) skill logic.
- **FR-014**: Unknown or cross-domain Skill ids MUST be rejected; the system MUST NOT fuzzy-map them to another Skill.
- **FR-015**: Skill validation failures (e.g. missing required medicine) MUST produce clarification or structured validation errors—not silent skill switching.
- **FR-016**: Pharmacy Domain Pack MUST provide an initial Skill catalog including at least: Consultations, Interactions, Dosage, Pregnancy, Lactation, Contraindications, Warnings, Side Effects, Storage, Alternatives, Leaflet.
- **FR-017**: Pharmacy recommend-mode behavior (020) MUST be reachable only through an explicitly selected recommend-capable Skill (e.g. Alternatives), never via automatic intent detection.
- **FR-018**: Skill id and Metadata Profile id MUST be recorded in quality/diagnostic trace surfaces for attribution (018/019).
- **FR-019**: External answer **responses** MUST remain compatible with the frozen field-level contract (015); Skill selection is an additive **request** input.
- **FR-020**: When profile-filtered retrieval yields insufficient evidence, the system MUST NOT silently drop filters to search the entire corpus unless the Skill’s bound profile explicitly defines a controlled fallback policy.

### Key Entities *(include if feature involves data)*

- **Domain Pack**: Domain-owned configuration bundle (pharmacy, legal, finance, …) loaded by the engine.
- **Skill**: Named retrieval capability within a Domain Pack; references a Metadata Profile; binds validation, prompt/template, output policy, and optional strategy constraints.
- **Skill Registry**: Per-domain catalog of Skills exposed to UI/API for explicit selection.
- **Metadata Profile**: Reusable filter/targeting definition (fields, sources, and related retrieval constraints) referenced by one or more Skills.
- **Selected Skill Binding**: Per-request authoritative Skill id from the client, resolved against the project’s domain registry.
- **Parsed Entities / Slots**: Structured entities extracted from the query under the Skill (e.g. medicines); does not include inferred intent for routing.
- **Skill Validation Rules**: Declarative requirements (e.g. require at least one medicine; require two medicines for interactions) evaluated after parse.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture layer boundaries; domain skill content lives in Domain Packs, not engine hardcoding.
- **NFR-002**: I/O-bound operations MUST be async; public APIs MUST include type hints.
- **NFR-003**: External providers (LLM, embedding, vector DB, reranker) MUST remain swappable via existing factory interfaces.
- **NFR-004**: RAG answer paths MUST return source citations when retrieval is used.
- **NFR-005**: Project/system prompts and Skill-bound prompt templates MUST be versioned when modified.
- **NFR-006**: Unit and integration tests MUST cover Skill resolution, rejection of missing/unknown Skills, entity-only parse under Skill, profile filter application, and non-invocation of skill classifiers.
- **NFR-007**: Structured logging MUST include correlation ids plus Skill id and Metadata Profile id at service boundaries.
- **NFR-008**: Secrets MUST NOT be stored in source control.
- **NFR-009**: Skill-constrained retrieval SHOULD reduce candidate volume versus unconstrained search for the same query, improving precision and reducing rerank/LLM cost (measured in Success Criteria).
- **NFR-010**: Feature MUST NOT introduce a parallel production answer/retrieval path (016 M0 freeze).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In Skills-enabled domains, 100% of successful answer requests include an explicitly client-selected Skill; 0% of Skill selections are produced by server-side intent/skill classifiers.
- **SC-002**: For a fixed Interactions evaluation set, profile-filtered retrieval returns at least 30% fewer irrelevant-field candidates (e.g. pure dosage-only chunks) than unconstrained field search, without reducing interaction-evidence recall below an agreed baseline on that set.
- **SC-003**: Median time-to-first-token or end-to-end answer latency for Skill-scoped pharmacy questions improves by at least 15% versus the same questions under unconstrained retrieval (same hardware and models), attributable to fewer candidates entering rerank/generation.
- **SC-004**: On a multilingual entity extraction golden set under fixed Skills, entity extraction F1 is at least as high as the prior intent+entity parser path, while skill-routing accuracy is 100% by construction (explicit selection).
- **SC-005**: Pack maintainers can add or retarget a Skill’s filters by editing only a Metadata Profile in at least 90% of filter-evolution cases without changing Skill identity.
- **SC-006**: Users complete Skill selection + question in under 30 seconds for common pharmacy tasks (Interactions, Dosage, Pregnancy) in moderated UX testing, with ≥90% first-attempt task success.
- **SC-007**: Zero production code paths remain that auto-assign pharmacy recommend-mode or interaction intent for Skill-enabled projects once the feature is active.

---

## Assumptions

- Projects are already bound to a Domain Pack (002); Skill registry is resolved from that domain.
- For v1, Skill selection is **per request** and also sticky in the UI until the user changes it; API clients send the Skill on each request.
- Domains with an empty or absent Skill registry do not require Skill selection (backward-compatible generic behavior) until a registry is published.
- Pharmacy initial Skills map conceptually as follows (names may be localized in UI):
  - **Interactions** → drug interaction capability / `drug_interactions` profile
  - **Dosage**, **Pregnancy**, **Lactation**, **Contraindications**, **Warnings**, **Side Effects**, **Storage**, **Leaflet** → corresponding leaflet-section profiles
  - **Alternatives** → 020 recommend-capable Skill (explicit only)
  - **Consultations** → broader counseling-oriented Skill with a wider or multi-field profile, still explicitly selected
- Metadata field names used in profiles align with existing chunk metadata conventions (e.g. `field: interactions`) and may evolve via profiles without Skill renames.
- Additive API request field for Skill id is allowed; frozen response fields from 015 are unchanged.
- Hybrid retrieval and reranking remain available inside Skill-constrained candidate sets (constitution VI); Skills narrow *what* is searched, not whether hybrid/rerank exist.
- Existing regex/YAML intent trees and parser intent mapping become non-authoritative for Skill-enabled domains and are scheduled for retirement rather than running in parallel as a second router (016).
- Illustrative pack layout for authors (not a mandated filesystem contract in this spec): domain pack contains `skills/` and `profiles/` sets resolved by the pack loader.

---

## Dependencies

- Domain Pack / Field Registry model (002)
- Sole Answer + Retrieval ownership and M0 freeze (016)
- Query Understanding stage (004) — narrowed under Skills
- Retrieval Planner / Engine (009 / 010)
- Answer Generation prompt binding (013)
- Frozen answer response contract (015) — additive request only
- Quality/eval surfaces (018 / 019)
- Pharmacy recommendation capability semantics (020) — explicit Skill invocation only
