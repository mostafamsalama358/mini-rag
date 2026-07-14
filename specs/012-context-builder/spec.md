# Feature Specification: Context Builder

**Feature Branch**: `012-context-builder`

**Created**: 2026-07-14

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Budget-Constrained Context Assembly (Priority: P1)

A downstream Answer Generation stage (013) receives an `EvidencePack` whose total token
count exceeds the configured model budget. The Context Builder must trim, compress, and
re-order the evidence so the resulting `Context` object fits within budget while retaining
the highest-value items.

**Why this priority**: This is the core reason the component exists. Without budget
enforcement, Answer Generation will fail at prompt injection or silently truncate mid-item,
breaking citation integrity.

**Independent Test**: Given a synthetic `EvidencePack` with 20 items totalling 12 000
tokens and a 4 000-token budget, the output `Context` must contain ≤ 4 000 tokens,
include the top-ranked items, and have no broken citation references — verifiable with a
unit test requiring no live LLM.

**Acceptance Scenarios**:

1. **Given** an `EvidencePack` with items ranked highest-to-lowest relevance and a total
   token count exceeding budget, **When** Context Builder runs, **Then** the emitted
   `Context.token_count` ≤ configured budget and all included items appear in the citation
   map.
2. **Given** items with varying `compressibility_score` values, **When** the budget is
   tight, **Then** high-compressibility items are compressed or dropped before
   low-compressibility items, verifiable by comparing the included item list to the
   original rank order.
3. **Given** an `EvidencePack` whose items already fit within budget, **When** Context
   Builder runs, **Then** all items are included unmodified and no compression is applied.

---

### User Story 2 — Conflict Detection and Disclosure (Priority: P2)

Answer Generation must not silently reconcile contradictory evidence (e.g., two items
citing different dosages for the same drug, or different prices for the same product).
Context Builder surfaces conflicts so Answer Generation can disclose disagreement to the
user.

**Why this priority**: Silent contradictions are a safety and trust risk in any RAG
answer. Detection here decouples conflict handling from the LLM prompt, enabling
deterministic tests.

**Independent Test**: Given two `EvidenceItem` objects that reference the same entity with
conflicting values, the output `Context.conflicts` list must contain exactly one
`ConflictGroup` identifying both items — testable without a running LLM.

**Acceptance Scenarios**:

1. **Given** two items sharing the same `entity_id` but with different attribute values,
   **When** Context Builder runs, **Then** `Context.conflicts` contains a `ConflictGroup`
   referencing both item ids.
2. **Given** an `EvidencePack` with no contradicting items, **When** Context Builder runs,
   **Then** `Context.conflicts` is empty.
3. **Given** a conflict group, **When** both conflicting items survive budget selection,
   **Then** both are preserved in the context with the conflict flag attached so Answer
   Generation can handle disclosure.

---

### User Story 3 — Coherent Document-Structure Ordering (Priority: P2)

Surviving items must be ordered by document hierarchy (`section_path`) rather than
relevance rank alone, so the assembled context reads as a coherent passage rather than
disconnected relevance-sorted fragments.

**Why this priority**: LLM comprehension degrades when context jumps between unrelated
sections. Structural ordering improves answer quality and reduces hallucination without
losing citation integrity.

**Independent Test**: Given items from two documents with known `section_path` values,
the ordered context must interleave items document-first, then section-depth order, with
no item missing from the output — verifiable without a running LLM.

**Acceptance Scenarios**:

1. **Given** items from multiple documents, **When** Context Builder stitches, **Then**
   items from the same document appear in consecutive blocks ordered by `section_path`.
2. **Given** items with no `section_path`, **When** stitching, **Then** ordering falls
   back to relevance rank with no error.

---

### User Story 4 — Final-Pass Duplicate Safety Net (Priority: P3)

Near-duplicate items that survived Evidence Orchestrator at a looser threshold must be
removed before the context is assembled, so the LLM does not receive redundant text that
wastes tokens.

**Why this priority**: A safety net with a configurable similarity threshold lower than
the Orchestrator's — ensures the budget is not wasted on near-identical items. Less
critical than core budget enforcement but necessary for quality.

**Independent Test**: Given two items with cosine similarity above the configured
final-pass threshold, only the higher-ranked item appears in the assembled context.

**Acceptance Scenarios**:

1. **Given** two items with similarity above threshold, **When** final dedup runs,
   **Then** the lower-ranked duplicate is dropped and its citation does not appear in
   `Context.citation_map`.
2. **Given** two items below threshold, **When** final dedup runs, **Then** both are
   retained.

---

### Edge Cases

- What happens when the `EvidencePack` is empty? → Emit an empty `Context` with
  `token_count = 0`, no items, no conflicts, and a warning in structured logs.
- What happens when every item is high-compressibility and compression still leaves the
  context over budget? → Drop lowest-ranked items until budget is satisfied; log a
  `CONTEXT_HARD_DROP` event with item ids.
- What happens when `IContextCompressor` raises an error for an item? → Fall back to
  inclusion of the original uncompressed item if it fits; otherwise drop it and log
  the error with the item id. Never propagate a compression error to the caller.
- What happens when two items in a conflict group have different `compressibility_score`
  values and one must be dropped for budget? → Drop the higher-compressibility item
  first even within a conflict group; the conflict is resolved by omission, and
  `Context.conflicts` records the dropped item as `resolution: "budget_drop"`.
- What happens when `section_path` is absent on some items but present on others? →
  Items with `section_path` are ordered first within their document; items without fall
  to the end of their document block.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a single `EvidencePack` (schema v1.0.0 from spec 011)
  as input and emit a single `Context` object as output.
- **FR-002**: System MUST compute a token budget by subtracting reserved space for
  system prompt, user question, and model output from the total configured model
  context window; the reserved sizes MUST be configurable.
- **FR-003**: System MUST select `EvidencePack.items` in ranked order until the budget
  is exhausted, preferring to drop or compress items with higher `compressibility_score`
  before dropping lower-scored items.
- **FR-004**: System MUST invoke `IContextCompressor` on any item flagged with a
  `compressibility_score` above the configured threshold before deciding to drop it;
  if the compressed form fits the budget it MUST be included.
- **FR-005**: System MUST detect conflicting items (same entity with differing attribute
  values) using `IConflictDetector` and populate `Context.conflicts`.
  `IConflictDetector` derives entity identity exclusively from `EvidenceItem.entity_tags`
  (entity identifiers supplied by spec 008 / spec 011) — it MUST NOT require any
  additional fields not present in the spec 011 `EvidenceItem` schema. The `attribute`
  label in `ConflictGroup` is a heuristic derived from the entity tag's type/category
  combined with text-pattern matching on the item content; no structured attribute
  key-value store is required from upstream.
- **FR-006**: System MUST order surviving items via `IContextStitcher` using
  `section_path` and document identity as primary sort keys, with relevance rank as
  tiebreaker.
- **FR-007**: System MUST perform a final-pass duplicate removal using configurable
  similarity threshold before assembly; the threshold MUST default to a value lower than
  the Evidence Orchestrator dedup threshold.
- **FR-008**: System MUST preserve a `Citation` object for every included item, mapped
  1:1 in `Context.citation_map`; no included item may appear without a corresponding
  citation entry.
- **FR-009**: System MUST populate `Context.metadata` with: count of items included,
  count of items dropped, count of items compressed, and whether any conflicts were
  detected.
- **FR-010**: System MUST expose four pluggable interfaces:
  `ITokenBudgetAllocator`, `IContextCompressor`, `IConflictDetector`, `IContextStitcher`.
- **FR-011**: System MUST NOT perform retrieval, re-ranking, deduplication at the
  Evidence Orchestrator level, or emit any LLM call — those responsibilities belong to
  upstream (011) and downstream (013) stages.
- **FR-012**: All domain-specific behavior MUST be injected via configuration
  (`context_builder.yaml` field-pack config), not hard-coded.

### Key Entities

- **`Context`**: The output contract consumed by Answer Generation (013). Contains:
  `ordered_blocks: list[ContextBlock]`, `citation_map: dict[str, Citation]`,
  `token_count: int`, `conflicts: list[ConflictGroup]`, `metadata: ContextMetadata`.
- **`ContextBlock`**: A single text unit in the assembled context. Contains:
  `item_id: str`, `text: str`, `token_count: int`, `compressed: bool`,
  `section_path: str | None`, `document_id: str`.
- **`ConflictGroup`**: Two or more items that contradict each other on the same entity.
  Contains: `entity_id: str`, `attribute: str`, `item_ids: list[str]`,
  `resolution: str | None` (e.g., `"budget_drop"`, or `None` if both survive).
- **`ContextMetadata`**: Diagnostic payload attached to every `Context`. Contains:
  `items_included: int`, `items_dropped: int`, `items_compressed: int`,
  `conflicts_detected: bool`, `budget_used: int`, `budget_total: int`.
- **`ITokenBudgetAllocator`**: Interface that receives model config and reservation
  config; returns `available_budget: int`.
- **`IContextCompressor`**: Interface that receives an `EvidenceItem` and target token
  count; returns compressed text and actual token count.
- **`IConflictDetector`**: Interface that receives a list of `EvidenceItem`; returns
  `list[ConflictGroup]`.
- **`IContextStitcher`**: Interface that receives a list of `EvidenceItem`; returns
  ordered `list[ContextBlock]`.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Context Builder MUST respect Clean Architecture boundaries — domain
  models (`Context`, `ContextBlock`, etc.) in domain layer; pipeline orchestration in
  application layer; compressor implementations in infrastructure layer.
- **NFR-002**: All pipeline stages MUST be `async`; all public methods MUST carry type
  hints.
- **NFR-003**: `IContextCompressor` implementations (LLM-based and heuristic) MUST be
  swappable via factory without modifying the pipeline.
- **NFR-004**: Every `Context` emitted on a RAG answer path MUST carry a populated
  `citation_map`; broken or missing citations are a hard error.
- **NFR-005**: Configuration (budget sizes, compressibility threshold, dedup threshold,
  compression strategy) MUST be field-pack injectable via `context_builder.yaml`.
- **NFR-006**: Unit tests MUST cover: budget allocation, selection under budget,
  compressor fallback, conflict detection, stitching order, final dedup, and citation
  map completeness. Integration tests MUST cover end-to-end pipeline with a mock
  `EvidencePack`.
- **NFR-007**: Structured logs MUST include `plan_id`, `pack_id`, `items_in`,
  `items_out`, `token_budget`, `compression_applied`, and any `CONTEXT_HARD_DROP`
  events.
- **NFR-008**: No secrets; no hard-coded model names; model context window size MUST be
  configuration-driven.
- **NFR-009**: Pipeline MUST complete within a configurable timeout; if exceeded,
  partial results MUST be emitted with `metadata.timeout = true` rather than raising an
  exception to the caller.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given an `EvidencePack` exceeding budget by any amount, the emitted
  `Context.token_count` is ≤ configured budget in 100% of test cases across the golden
  query set (spec 014).
- **SC-002**: Highest-ranked items (top quartile by relevance score) are preserved in
  the final context in ≥ 95% of cases where budget permits at least one item.
- **SC-003**: Zero broken citations — every `ContextBlock.item_id` has a corresponding
  entry in `Context.citation_map` — verified on every run of the golden query set.
- **SC-004**: Conflict detection recalls ≥ 90% of injected conflicts in the golden
  query set (synthetic contradictions covering entity/attribute overlap).
- **SC-005**: Context assembly (excluding LLM-based compression calls) completes in
  ≤ 150 ms p95 on a 50-item `EvidencePack`, measured in unit benchmarks without live
  external calls.
- **SC-006**: Graceful degradation is measurable: when budget forces drops, items
  dropped are ranked in the bottom 50% by relevance score in ≥ 90% of cases.

## Assumptions

- `EvidencePack` schema v1.0.0 (spec 011) is stable and consumed as-is with **no schema
  extension required**. Conflict detection derives entity identity from the existing
  `EvidenceItem.entity_tags` field (entity identifiers from spec 008 KnowledgeUnit
  tags). The `attribute` label in `ConflictGroup` is a heuristic derived from the entity
  tag's type/category and text-pattern analysis of `EvidenceItem.text`; it does not
  require a structured attribute-value field on `EvidenceItem`. If spec 011 later adds
  explicit attribute-value pairs to `entity_tags`, `IConflictDetector` implementations
  MAY use them, but the interface contract does not depend on them.
- `EvidenceItem.compressibility_score` is a float in [0, 1] populated by Evidence
  Orchestrator; Context Builder trusts this value without re-computing it.
- Token counting uses the same character-approximation or tiktoken strategy already in
  the codebase; a `ITokenCounter` interface (from spec 011 token-counting module) is
  reused rather than duplicated.
- LLM-based compression (summarization) is one optional `IContextCompressor`
  implementation; a heuristic truncation compressor is the default to avoid adding a
  mandatory LLM call in the context-building stage (keeps latency deterministic).
- `Citation` schema is inherited directly from `EvidencePack.items[*].citation`; Context
  Builder does not define a new citation schema.
- Model context-window sizes are configuration-driven; the component does not hard-code
  any model name or window size.
- Field-pack YAML (`context_builder.yaml`) follows the same generic < domain < project
  override hierarchy established in spec 002 (Field Registry).
- Answer Generation (spec 013) is not yet implemented; the `Context` schema defined
  here is the stable contract that spec 013 will consume.
- Spec 014 (Answer Quality) golden query set will be used for end-to-end validation;
  Context Builder spec does not define that set.
