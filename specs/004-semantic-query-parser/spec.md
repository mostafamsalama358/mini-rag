# Feature Specification: Semantic Query Parser

**Feature Branch**: `004-semantic-query-parser`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "Design the Query Understanding stage from first principles. Replace the current multi-stage pipeline (regex, intents, YAML rules, rewrite logic, follow-up heuristics, entity extraction, field resolution) with a single semantic parsing stage that produces a canonical query and deterministic structured QueryPlan for retrieval. Support Arabic, English, and mixed-language questions. Evaluate LLM-only vs hybrid approaches."

## Executive Summary

The Query Understanding stage SHALL be redesigned as a **single semantic parsing boundary** between conversational user input and retrieval. The parser accepts natural-language questions (Arabic, English, or mixed) plus conversation context, and produces two outputs consumed exclusively by downstream retrieval:

1. **Canonical Query** — a normalized, document-language search string optimized for recall against indexed content.
2. **QueryPlan** — a deterministic, schema-validated structure describing *what* to retrieve (entity, field/concept, operation, scope, language).

The current implementation — layered regex intents, large YAML synonym maps, separate rewrite/entity/field-resolution passes, and follow-up heuristics — is **not preserved**. This specification defines the simplest architecture that meets retrieval needs while acknowledging where a **thin deterministic validation layer** may still be required for safety and repeatability.

### Architectural Verdict

| Approach | Verdict |
| -------- | ------- |
| **Pure LLM semantic parser** | Preferred core design — dramatically reduces maintenance surface and handles multilingual/mixed input naturally. |
| **Current multi-stage pipeline** | Superseded — high coupling, duplicate vocabulary (intents + fields + rewrite prompts), and reactive patch loops. |
| **Recommended hybrid** | LLM parser **plus** schema validation, entity grounding against project catalog, and deterministic fallbacks on parse failure — **not** a return to regex intent trees. |

**Why the single-stage design is architecturally superior**

- **One vocabulary**: Field concepts, operations, and entity references are declared once in a field registry; the parser maps language to that registry instead of maintaining parallel synonym lists across multiple YAML files.
- **One extension point**: Adding a new retrievable concept is a registry declaration plus parser prompt/schema update — not new regex rules, intent buckets, and grounding configs.
- **Context-native**: Follow-up resolution ("what interacts with it?") is a conversation-context input to the parser, not a separate carry-over heuristic chain.
- **Retrieval contract clarity**: The retriever reads **QueryPlan only** for filters, scope, and field targeting; the canonical query feeds hybrid search text only.

**Known weaknesses of LLM-only parsing (and mitigations)**

| Weakness | Risk | Mitigation (in scope) |
| -------- | ---- | --------------------- |
| Non-determinism | Same question may yield slightly different plans across runs | Low-temperature generation, structured output schema, golden-set regression tests, optional response caching keyed by normalized input + context hash |
| Entity hallucination | Parser invents drug names not in the catalog | Post-parse **entity grounding**: fuzzy-match `entity` against project catalog; reject or clarify if no match above confidence threshold |
| Latency | Adds model round-trip before retrieval | Hard timeout with degraded fallback; async pipeline; target ≤2s p95 for parse stage |
| Field drift | Parser picks valid-sounding but unindexed concepts | QueryPlan `field` MUST be validated against the active field registry; unknown fields trigger clarification or `field: unknown` path |
| Cost at scale | Every query invokes a model | Acceptable for conversational RAG; batch/offline paths may skip parser |
| Over-trust in canonical query | Redundant or conflicting signals if retriever uses both plan and text | Retriever treats QueryPlan as authoritative for structured filters; canonical query is for lexical/semantic search only |

A **hybrid** that retains large regex/YAML intent layers alongside the LLM parser would reintroduce dual maintenance and conflicting decisions. The recommended hybrid is **LLM-first with deterministic guardrails**, not parallel rule engines.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Direct entity question in Arabic (Priority: P1)

A pharmacist asks about a specific drug attribute in colloquial Arabic. The system understands intent and entity without the user naming the field in catalog terms.

**Why this priority**: Core value proposition — natural multilingual questions must work without users learning schema vocabulary.

**Independent Test**: Submit `"ايه كل تركيزات يوثيروكس؟"` with no prior context. Verify parser output and successful retrieval of strength data for EUTHYROX.

**Acceptance Scenarios**:

1. **Given** an indexed pharmacy project with EUTHYROX in the catalog, **When** the user asks `"ايه كل تركيزات يوثيروكس؟"`, **Then** the system produces canonical query `"List all strengths of EUTHYROX."` and QueryPlan `{ entity: "EUTHYROX", field: "strengths", operation: "list", scope: "all", language: "en" }`, and retrieval returns strength-related chunks for EUTHYROX.
2. **Given** the same project, **When** the user asks in English `"What strengths does Euthyrox come in?"`, **Then** the QueryPlan is equivalent (same entity, field, operation, scope) modulo casing normalization on entity.

---

### User Story 2 - Follow-up using conversation context (Priority: P1)

A user asks a pronoun/reference follow-up after establishing an entity in the prior turn.

**Why this priority**: Multi-turn conversation is essential for pharmacy workflows; context resolution must not depend on fragile regex reference patterns.

**Independent Test**: Turn 1: `"Tell me about EUTHYROX"`. Turn 2: `"ايه الادوية المتعارضة معاه؟"`. Verify entity carry-over and interactions field resolution.

**Acceptance Scenarios**:

1. **Given** conversation context with `current_entity = EUTHYROX`, **When** the user asks `"ايه الادوية المتعارضة معاه؟"`, **Then** canonical query is `"List all drug interactions of EUTHYROX."` and QueryPlan `{ entity: "EUTHYROX", field: "interactions", operation: "list", scope: "all", language: "en" }`.
2. **Given** a follow-up with ambiguous reference and no resolvable entity in context, **When** the user asks `"what are its side effects?"`, **Then** the system requests clarification rather than guessing an entity.

---

### User Story 3 - Mixed-language and colloquial input (Priority: P2)

A user mixes Arabic and English or uses transliterated brand names.

**Why this priority**: Real users code-switch; the parser must normalize without separate Arabic/English pipelines.

**Independent Test**: Submit `"يوثيروكس interactions ايه؟"` and verify correct interactions QueryPlan.

**Acceptance Scenarios**:

1. **Given** a catalog containing EUTHYROX, **When** the user asks `"يوثيروكس interactions ايه؟"`, **Then** entity resolves to EUTHYROX and field resolves to interactions.
2. **Given** Arabic digits and diacritics in input, **When** the question is otherwise clear, **Then** lightweight deterministic text normalization runs **before** parsing (digits, whitespace, diacritics only — not intent/field rules).

---

### User Story 4 - Parser failure and clarification (Priority: P2)

When the parser cannot produce a valid grounded QueryPlan, the user receives a helpful clarification instead of a wrong retrieval.

**Why this priority**: Safety and trust — wrong drug entity or field is high-impact in pharmacy domain.

**Independent Test**: Submit gibberish or ask about a drug not in the catalog; verify clarification path.

**Acceptance Scenarios**:

1. **Given** a query mentioning a drug not in the project catalog, **When** entity grounding fails, **Then** the system asks the user to confirm or correct the drug name (clarification response), not retrieve unrelated content.
2. **Given** parser timeout or invalid schema output, **When** fallback activates, **Then** the system either retries once, uses a minimal safe fallback (canonical query = normalized user text, QueryPlan with `field: unknown`), or asks for rephrasing — never silently inventing structured filters.

---

### User Story 5 - Domain-agnostic field packs (Priority: P3)

A non-pharmacy project (e.g., legal, generic) uses the same parser architecture with its own field registry.

**Why this priority**: Confirms the design is generic per platform constitution — not a pharmacy one-off.

**Independent Test**: Configure a legal field pack with concepts like `clause_type` and `jurisdiction`; ask a natural-language question; verify QueryPlan uses pack concepts.

**Acceptance Scenarios**:

1. **Given** a legal field registry declaring concepts `{clause, jurisdiction, penalty}`, **When** a user asks a question about penalties in a statute, **Then** QueryPlan `field` is one of the declared concepts and retrieval filters accordingly.
2. **Given** a generic project with minimal registry, **When** the user asks a broad question, **Then** QueryPlan may use `field: unknown` and retrieval relies primarily on canonical query text (graceful degradation).

---

### Edge Cases

- Empty or whitespace-only user input → clarification prompt, no retrieval.
- User switches entity mid-conversation → parser updates `current_entity` from explicit mention; implicit references use most recently established entity.
- User asks for multiple entities in one question ("compare X and Y") → QueryPlan supports `entities: [X, Y]` and `operation: compare` (see Key Entities); retriever handles multi-entity scope.
- User asks exhaustive list without naming entity ("list all antibiotics") → `scope: all`, `entity: null` or category entity if registry supports taxonomies.
- Document language differs from question language → canonical query uses **document language** (e.g., English for English-indexed catalogs) regardless of user input language.
- Very long conversational history → parser receives a bounded context window (recent turns + established entities), not full transcript.
- Adversarial or off-topic input → parser returns `operation: unsupported` or clarification; no retrieval on harmful/irrelevant plans.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Parser Inputs & Outputs

- **FR-001**: System MUST expose a Query Understanding stage that accepts: (a) raw user question text, (b) conversation context (at minimum: established entities, prior QueryPlans or canonical queries from recent turns, document language), and (c) active field registry for the project domain.
- **FR-002**: System MUST produce a **Canonical Query** string in the project's document language, optimized for retrieval recall against indexed content.
- **FR-003**: System MUST produce a **QueryPlan** conforming to a versioned, documented schema (see Key Entities).
- **FR-004**: Downstream retrieval MUST consume **QueryPlan** as the sole source of structured retrieval intent (entity, field, operation, scope, filters). Canonical query MUST be used only for lexical and semantic search text, not for structured filter logic.
- **FR-005**: System MUST support user questions in Arabic, English, and mixed Arabic/English in a single code path — no separate language-specific intent pipelines.

#### Semantic Parsing Behavior

- **FR-006**: System MUST determine user intent (lookup, list, compare, explain, etc.) as part of semantic parsing, expressed as QueryPlan `operation`.
- **FR-007**: System MUST resolve conversational references (pronouns, "with it", "معاه", implicit entity) using supplied conversation context, not regular-expression reference patterns.
- **FR-008**: System MUST resolve the requested information type to a registry-backed `field` (concept) — e.g., strengths, interactions, warnings — not to raw database column names in the QueryPlan.
- **FR-009**: System MUST normalize entity names to catalog canonical forms (e.g., Arabic colloquial → `EUTHYROX`) during parsing or grounding.
- **FR-010**: System MUST set QueryPlan `language` to the document language used for canonical query and retrieval (not necessarily the user's input language).

#### Validation & Grounding (Hybrid Guardrails)

- **FR-011**: System MUST validate every QueryPlan against the active field registry; `field` values not in the registry MUST NOT proceed to filtered retrieval without clarification or explicit `unknown` handling.
- **FR-012**: System MUST ground QueryPlan `entity` (when present) against the project catalog; if no catalog match meets the configured confidence threshold, system MUST trigger user clarification.
- **FR-013**: System MAY apply deterministic pre-parse normalization limited to: Unicode normalization, Arabic diacritic stripping, digit transliteration, and whitespace collapse. Pre-parse normalization MUST NOT encode domain intents, field synonyms, or entity patterns.
- **FR-014**: On parser failure (timeout, invalid schema, model error), system MUST follow a defined degradation path: retry → clarification → minimal unscoped retrieval — in that preference order. System MUST NOT fabricate grounded entities or fields.

#### Conversation Context

- **FR-015**: System MUST maintain conversation context including at least one `current_entity` when established by prior turns or explicit user mention.
- **FR-016**: System MUST pass bounded conversation context into the parser (configurable turn window) to resolve follow-ups without re-scanning full chat history with heuristics.

#### Deprecation of Current Pipeline

- **FR-017**: System MUST NOT require per-domain regex intent classification, multi-hundred-line query rewrite YAML, or parallel field-resolution synonym matching as part of the new Query Understanding stage.
- **FR-018**: Field registry (`fields.yaml` or successor) remains the declarative source of retrievable concepts and catalog metadata keys; it is consumed by the parser (as allowed values) and retriever (as column/filter mapping), not duplicated in rewrite/intent YAML.

#### Observability & Testing

- **FR-019**: System MUST log parser inputs (redacted), canonical query, QueryPlan, grounding decisions, and latency for every query.
- **FR-020**: System MUST support a golden evaluation set: curated (question, context) → expected QueryPlan pairs for regression testing across Arabic, English, and mixed inputs.

### Key Entities

- **QueryPlan**: Structured retrieval intent. Required fields:
  - `entity` (string | null) — canonical catalog identifier for the primary subject; null when listing across entities or not applicable.
  - `entities` (string[], optional) — for multi-entity operations (compare, interaction-between).
  - `field` (string) — registry-backed concept key (e.g., `strengths`, `interactions`, `warnings`) or `unknown`.
  - `operation` (enum) — `lookup` | `list` | `compare` | `explain` | `count` | `unsupported`.
  - `scope` (enum) — `all` | `single` | `subset` — whether the user wants exhaustive enumeration or a focused answer.
  - `language` (string) — ISO 639-1 document language for canonical query (e.g., `en`, `ar`).
  - `filters` (object, optional) — structured qualifiers (e.g., strength value, dosage form) when explicitly requested.
  - `confidence` (number, optional) — parser self-assessed confidence; used for clarification thresholds.
  - `needs_clarification` (boolean) — when true, downstream retrieval is skipped and user is prompted.
  - `clarification_prompt` (string, optional) — user-facing message when clarification is needed.

- **Canonical Query**: Single string in document language; human-readable; used as hybrid retrieval search text. Example: `"List all drug interactions of EUTHYROX."`

- **Conversation Context**: Bounded structure passed to parser:
  - `current_entity` (string | null)
  - `recent_turns` (ordered list of prior user questions and resulting QueryPlans or canonical queries)
  - `document_language` (string)
  - `project_domain` (string) — selects field registry profile

- **Field Registry Profile**: Declarative domain vocabulary — allowed `field` concepts, entity metadata keys, output shapes (list vs prose), interaction patterns. Consumed by parser validation and retriever mapping. Replaces duplicate synonym/intent YAML for query understanding purposes.

- **Catalog Entry**: Project-indexed entity record used for grounding (brand names, synonyms, identifiers in multiple languages).

### Non-Functional Requirements

- **NFR-001**: Query Understanding MUST be a single bounded stage with one primary semantic parser; deterministic logic limited to normalization, schema validation, and catalog grounding.
- **NFR-002**: Parse stage p95 latency MUST be ≤2 seconds under normal operating conditions, including model round-trip.
- **NFR-003**: For golden-set regression tests, QueryPlan field and entity MUST match expected values in ≥95% of cases; operation and scope in ≥90%.
- **NFR-004**: Parser output MUST be schema-validated before retrieval; invalid plans MUST NOT reach the retriever.
- **NFR-005**: Architecture MUST support multiple domain field packs without code changes to the parser core — only registry and prompt/schema configuration.
- **NFR-006**: Structured logging MUST include correlation id, parse latency, grounding outcome, and whether clarification was triggered.
- **NFR-007**: The design MUST remain consistent with platform Clean Architecture: Query Understanding lives in core/application layer; domain vocabulary in field packs; no retrieval implementation details inside the parser.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Median time from user submit to start of retrieval decreases or stays flat versus the current multi-stage pipeline, with parse stage p95 ≤2 seconds.
- **SC-002**: On a curated golden set of at least 50 pharmacy questions (Arabic, English, mixed), ≥95% produce the correct `entity` and `field` in QueryPlan without human correction.
- **SC-003**: On a curated set of at least 20 multi-turn follow-up conversations, ≥90% correctly resolve implicit entity references without user re-stating the drug name.
- **SC-004**: Adding a new retrievable concept to a domain requires editing the field registry and parser allowed-values only — zero new regex rules or intent YAML blocks — validated by a documented smoke test per new concept.
- **SC-005**: Total domain-specific query-understanding configuration surface reduced by ≥80% compared to the pre-redesign baseline for the pharmacy domain.
- **SC-006**: When entity grounding fails, 100% of cases trigger clarification or explicit user confirmation — never silent retrieval against a wrong entity.
- **SC-007**: Non-pharmacy domain (legal or generic) achieves successful QueryPlan generation on at least 10 representative questions using the same parser architecture.

---

## Assumptions

- Indexed document language is known per project (typically English for current pharmacy catalogs); canonical query targets that language.
- A project catalog or entity index is available for grounding (derived from indexed metadata); parser does not invent entities outside this set.
- The field registry remains the authoritative list of retrievable concepts; the retriever already maps concepts to storage columns (or will be adapted to consume QueryPlan in a follow-on implementation phase).
- LLM provider is available for semantic parsing with structured JSON output support; provider selection is configuration-driven.
- Clarification UX (asking user to confirm entity or rephrase) is acceptable latency-wise for ambiguous queries — better than wrong answers.
- Full removal of legacy query understanding code happens in implementation phase; this spec defines target architecture only.
- Comparison and multi-entity queries are in scope for QueryPlan schema but may be implemented in a later iteration if retrieval support is not yet ready — parser MUST still emit structured compare plans when detected.

## Out of Scope

- Redesign of hybrid retrieval, reranking, or answer generation — only the Query Understanding → Retrieval contract is specified here.
- Fine-tuning or training a custom parser model; v1 uses prompt + structured output from existing generation providers.
- Preserving backward compatibility with legacy intent names or regex behavior.
- User-facing display of QueryPlan or canonical query (internal artifacts only unless debugging mode).

## Dependencies

- Active field registry per domain (`fields/` packs).
- Project entity catalog derived from indexed document metadata.
- Conversation history store (existing chat message persistence).
- LLM generation provider with JSON/schema-constrained output.
- Retrieval engine adaptation to accept QueryPlan as structured input (planned follow-on work).
