# Feature Specification: Pharmacy Query Enhancement

**Feature Branch**: `001-pharmacy-query-enhancement`

**Created**: 2026-06-29

**Status**: Superseded

**Superseded by**: [`002-field-registry`](../002-field-registry/spec.md) — pharmacy behavior is **Phase D** (`fields/pharmacy/`). Do not implement this spec separately.

**Archived**: 2026-06-29

--- User description: "Enhance pharmacy RAG query retrieval with LLM query rewriting and improved prompts for exhaustive drug lists, interactions, and prescription analysis. The generic RAG system is deployed for pharmacy use with bilingual (Arabic/English) pharmacist prompts. Current failures: incomplete exhaustive lists (e.g., muscle relaxants returns 1 of 7+), inconsistent drug-interaction answers for the same drug, prescription cross-check misses pairwise interactions, and follow-up questions lose context."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exhaustive Drug Class Listing (Priority: P1)

A pharmacist asks in Arabic: "كل الادوية المصنفة كباسط للعضلات" (all drugs classified as muscle relaxants). The system must return **every** matching drug found across indexed pharmacy spreadsheets (e.g., `FINALMEDICIN.xlsx`), not a partial sample.

**Why this priority**: List completeness is the most visible failure in production chat logs and undermines trust in the pharmacy assistant.

**Independent Test**: Index known pharmacy Excel files, ask for a drug class with a known row count in source data, verify answer count matches source rows (±0) and cites correct source files.

**Acceptance Scenarios**:

1. **Given** indexed `FINALMEDICIN.xlsx` containing N muscle-relaxant rows, **When** the user asks for all muscle relaxants in Arabic, **Then** the answer lists all N drugs with no omissions and includes a Source Coverage section.
2. **Given** the same query repeated twice, **When** no data has changed, **Then** the answer set is identical (same drugs, same count).
3. **Given** no matching rows in indexed documents, **When** the user asks for a drug class, **Then** the system states clearly that the information is unavailable.

---

### User Story 2 - Complete Drug Interaction Lookup (Priority: P1)

A pharmacist asks: "عايز كل الادوية المتعارضة مع cordarone" or requests all active ingredients that interact with Cordarone (amiodarone). The system must retrieve and present **all** interactions documented in interaction spreadsheets (e.g., `NEWDRUGINTERACTION.xlsx`, `ALLMATERIAL1.xlsx`), including severity when available.

**Why this priority**: Incomplete interaction data is a patient-safety risk; current behavior returns 2–3 items when dozens may exist.

**Independent Test**: Query a drug with a known interaction count in source files; verify full enumeration and structured interaction fields (risk, mechanism, severity) when present in context.

**Acceptance Scenarios**:

1. **Given** `NEWDRUGINTERACTION.xlsx` indexed with M interactions for amiodarone/Cordarone, **When** the user asks for all conflicting drugs, **Then** all M interactions appear in the answer.
2. **Given** interactions differ across two source files, **When** both are retrieved, **Then** the answer identifies discrepancies and summarizes differences without favoring one source.
3. **Given** a follow-up "عايزهم كلهم مهما كان عددهم", **When** the prior turn was about Cordarone interactions, **Then** the system does not narrow results further; it expands retrieval if needed.

---

### User Story 3 - Prescription Interaction Cross-Check (Priority: P2)

A pharmacist pastes a prescription listing multiple brand-name drugs (e.g., Cordarone, Tryptizol, Averozolid, Lyrica, Alkapress) and asks which drugs in the list interact with each other.

**Why this priority**: Multi-drug prescription review is a core pharmacy workflow demonstrated in user chat logs.

**Independent Test**: Submit a fixed prescription string; verify pairwise interactions are reported only when documented in retrieved chunks.

**Acceptance Scenarios**:

1. **Given** a prescription with drugs A, B, C, D, E, **When** the user asks which drugs conflict with each other, **Then** the system parses all drug names, retrieves interaction data for each pair, and reports only documented conflicts.
2. **Given** some drugs are not in the knowledge base, **When** cross-checking, **Then** those drugs are listed as "information unavailable" while known drugs are still analyzed.
3. **Given** no documented pairwise interactions among the listed drugs, **When** cross-check completes, **Then** the system states clearly that no interactions were found in retrieved documents.

---

### User Story 4 - Bilingual Pharmacist Prompt & Output Format (Priority: P2)

The pharmacy project uses a custom bilingual pharmacist system prompt (English + Arabic) with structured sections: Summary, Details, Warnings, Source Coverage. Answers must follow medical safety rules (no prescribing advice, black-box warnings, approved vs unapproved uses).

**Why this priority**: Prompt quality governs answer structure and safety compliance; the user has already authored the prompt and expects it to drive behavior.

**Independent Test**: Configure project `prompt_override` with the pharmacist template; ask a drug comparison question; verify output sections and safety disclaimers.

**Acceptance Scenarios**:

1. **Given** a pharmacy project with custom `prompt_ar` / `prompt_en`, **When** the user asks in Arabic, **Then** the Arabic prompt is used and the answer follows # الملخص / # التفاصيل / # التحذيرات / # تغطية المصدر structure.
2. **Given** a medical question, **When** the LLM answers, **Then** it never recommends starting, stopping, or changing medication.
3. **Given** retrieved context supports a drug comparison, **When** the user compares two drugs, **Then** a Markdown table is used with available comparison fields.

---

### User Story 5 - Conversational Follow-Up Context (Priority: P3)

A pharmacist asks about a drug (e.g., "dimra استخدامات"), then follow-ups like "الجرعة الخاصة به" and "كام مرة في اليوم" without repeating the drug name.

**Why this priority**: Follow-up failures appear in logs but depend on chat history + better entity resolution.

**Independent Test**: Multi-turn session asking about one drug; verify later turns resolve the drug entity from history.

**Acceptance Scenarios**:

1. **Given** a session where the user asked about drug X, **When** they ask "what is the dose?" without naming X, **Then** retrieval targets drug X using session context.
2. **Given** ambiguous follow-up with multiple drugs in history, **When** context is insufficient, **Then** the system asks for clarification rather than guessing.

---

### Edge Cases

- Query uses colloquial Arabic drug names vs brand names vs INN (e.g., Cordarone vs amiodarone).
- Same drug spelled in Latin and Arabic script.
- Excel rows split across multiple chunks — exhaustive retrieval must merge rows from all relevant chunks.
- Very large interaction lists (100+ rows) — answer must still enumerate all items or paginate with explicit completeness statement.
- User asks for alternatives not stated in documents — system must refuse to invent alternatives.
- Hybrid search disabled — system degrades gracefully with vector-only retrieval.
- LLM query-rewrite timeout/failure — falls back to rule-based expansion without blocking the request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST classify pharmacy query intent (exhaustive list, drug detail, interaction lookup, prescription cross-check, comparison, general) before retrieval.
- **FR-002**: System MUST rewrite user queries into one or more retrieval-optimized search strings using an LLM step, preserving original language and entities.
- **FR-003**: System MUST detect exhaustive-list pharmacy patterns in Arabic and English (e.g., "كل الادوية", "all drugs", "عايزهم كلهم", "مهما كان عددهم") and trigger expanded retrieval limits.
- **FR-004**: System MUST run multi-query retrieval (original + rewritten + rule-based expansions) and merge/deduplicate results before reranking.
- **FR-005**: System MUST parse multi-drug prescription input into individual drug entities for pairwise interaction retrieval.
- **FR-006**: System MUST resolve follow-up queries using chat history when the current query omits the drug entity.
- **FR-007**: System MUST use project-level `prompt_override` (pharmacist template) when configured, per constitution prompt-versioning rules.
- **FR-008**: System MUST instruct the generation model to enumerate **all** items from **all** retrieved documents for exhaustive queries; partial lists are unacceptable when context contains more rows.
- **FR-009**: System MUST NOT add information absent from retrieved context (grounding rule from pharmacist prompt).
- **FR-010**: System MUST include source coverage metadata in answers (document count used) without exposing internal chunk IDs.
- **FR-011**: System SHOULD improve XLSX ingestion to preserve row boundaries (one chunk per row or fixed row groups) for pharmacy tabular files.
- **FR-012**: System MUST return structured API citations (file name, chunk metadata, scores) in addition to human-readable Sources section.

### Key Entities

- **QueryIntent**: Classification label, confidence, extracted entities (drugs, classes, active ingredients), rewritten queries, retrieval mode (standard | exhaustive | prescription).
- **PharmacyEntity**: Normalized drug reference (brand name, INN, Arabic alias) linked to search terms.
- **RetrievalPlan**: Original query, rewritten queries, per-query limits, target source files, metadata filters.
- **ProjectPrompt**: Versioned bilingual system prompt (`prompt_en`, `prompt_ar`) attached to a project.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture — query understanding in `services/`, retrieval extensions in `utils/`, no provider imports in controllers.
- **NFR-002**: LLM query rewrite MUST be async; public APIs MUST include type hints.
- **NFR-003**: Query rewriter MUST use existing `generation_client` interface; no hard-coded provider in services.
- **NFR-004**: RAG answer paths MUST return source citations in API responses.
- **NFR-005**: Pharmacist prompt changes MUST be persisted via `project_prompts` table.
- **NFR-006**: Unit tests for intent detection, query expansion, prescription parsing; integration tests for exhaustive list and interaction scenarios.
- **NFR-007**: Metrics MUST track query intent, rewrite latency, exhaustive retrieval doc counts.
- **NFR-008**: Query rewrite prompts MUST NOT log PHI or full prescription text at INFO level.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Exhaustive drug-class queries return ≥95% of source rows for benchmark test sets (muscle relaxants, antihypertensives) vs current ~15–30% baseline.
- **SC-002**: Repeated identical interaction queries for the same drug produce the same drug count in ≥99% of runs.
- **SC-003**: Prescription cross-check correctly identifies all documented pairwise interactions in a 5-drug benchmark prescription.
- **SC-004**: p95 answer latency increases by no more than 2 seconds vs baseline due to query rewrite (measured on staging).
- **SC-005**: 100% of pharmacy answers in benchmark set include Source Coverage section and medical safety disclaimers where applicable.

## Assumptions

- Pharmacy data remains in Excel format (`FINALMEDICIN.xlsx`, `NEWDRUGINTERACTION.xlsx`, `ALLMATERIAL1.xlsx`) with consistent column semantics.
- The existing hybrid retrieval (pgvector + FTS) and reranker remain enabled in production.
- LLM query rewrite uses the same generation provider already configured for answer generation.
- The user-authored pharmacist prompt will be stored as `project_prompts` for the pharmacy project.
- Re-indexing may be required after row-aware XLSX chunking changes.
