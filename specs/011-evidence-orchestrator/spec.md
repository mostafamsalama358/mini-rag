# Feature Specification: Evidence Orchestrator

**Feature Branch**: `011-evidence-orchestrator`

**Created**: 2026-07-14

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Deduplicated Evidence Pack from Multi-Strategy Retrieval (Priority: P1)

A system invoking the RAG pipeline issues a query that triggers two or more retrieval strategies (e.g., dense vector + BM25). Raw results from both strategies are fed into the Evidence Orchestrator, which returns a single deduplicated, ranked Evidence Pack where each content chunk appears at most once, with merged source attribution.

**Why this priority**: Deduplication is the core value proposition. Without it, downstream Context Builder (012) receives redundant tokens, degrading answer quality and wasting budget.

**Independent Test**: Feed synthetic retrieval output with deliberate exact and near-duplicate chunks from two strategies. Assert that the returned Evidence Pack contains no duplicates, that each surviving item's sources list is merged, and that the highest-scoring duplicate's score is preserved.

**Acceptance Scenarios**:

1. **Given** a Retrieval Plan with both dense-vector and BM25 strategies active, **When** both strategies return the same chunk (exact text match), **Then** the Evidence Pack contains that chunk exactly once with both strategy sources listed and the higher of the two scores retained.
2. **Given** two chunks whose text similarity exceeds the configured near-duplicate threshold, **When** the Orchestrator runs deduplication, **Then** only the higher-scoring chunk is kept in the Evidence Pack.
3. **Given** retrieval results with zero duplicates, **When** the Orchestrator runs deduplication, **Then** all chunks are passed through unchanged.

---

### User Story 2 — Ranked Evidence Pack with Relevance Fusion (Priority: P1)

After deduplication, the Evidence Orchestrator ranks surviving chunks by fusing retrieval scores with entity/relation relevance tags (from spec 008) and available recency/authority metadata, producing a final relevance score per item.

**Why this priority**: Ranking determines which evidence the Context Builder selects under token budget pressure; poor ranking directly causes answer degradation.

**Independent Test**: Supply deduplicated chunks with known retrieval scores and entity-match counts. Assert that the final Evidence Pack is sorted in descending order of final relevance score and that the score reflects both retrieval signal and entity relevance.

**Acceptance Scenarios**:

1. **Given** two chunks with equal retrieval scores but different entity-relevance tag matches, **When** the Orchestrator prioritizes them, **Then** the chunk with more entity matches ranks higher.
2. **Given** chunks with recency metadata present, **When** authority/recency boosting is configured, **Then** newer or higher-authority chunks receive a score boost.
3. **Given** chunks with no entity tags and no recency metadata, **When** the Orchestrator ranks them, **Then** ranking falls back gracefully to raw retrieval score order.

---

### User Story 3 — Adjacent Context Expansion for Truncated Chunks (Priority: P2)

When a high-relevance chunk appears truncated (its parent/child or prev/next links from spec 007 exist and the chunk score exceeds the expansion threshold), the Orchestrator optionally retrieves adjacent segments and appends them to the Evidence Item, providing fuller context without duplicating evidence.

**Why this priority**: Expansion prevents half-context answers on borderline chunks; it is optional and gated by a configurable threshold, so it can be disabled without affecting core pipeline correctness.

**Independent Test**: Provide a high-relevance chunk with known prev/next references. Configure expansion threshold below the chunk's score. Assert that the returned Evidence Item includes the adjacent text and that the adjacent segment is not emitted as an independent Evidence Item.

**Acceptance Scenarios**:

1. **Given** a chunk whose score exceeds the expansion threshold and whose parent chunk link exists, **When** the Orchestrator runs expansion, **Then** the Evidence Item's text includes the parent context prepended.
2. **Given** a chunk whose score is below the expansion threshold, **When** expansion runs, **Then** the chunk is returned as-is with no adjacent text added.
3. **Given** expansion is disabled via configuration, **When** the Orchestrator runs, **Then** no expansion occurs regardless of chunk scores.

---

### User Story 4 — Compressibility Flagging for Budget-Aware Downstream Processing (Priority: P2)

The Evidence Orchestrator detects low-value or highly redundant content among surviving chunks and attaches a `compressibility_score` to each Evidence Item, enabling the Context Builder (012) to decide which items to summarize or drop under token pressure.

**Why this priority**: Defers heavy compression logic to 012 while enabling it; the Orchestrator's role is to surface candidates, not to compress.

**Independent Test**: Supply a set of chunks where some are semantic near-duplicates of higher-scoring survivors (below dedup threshold) and others are low-relevance. Assert that low-value chunks carry a compressibility_score above a defined threshold and high-value chunks carry a score below it.

**Acceptance Scenarios**:

1. **Given** a surviving chunk whose content largely overlaps with a higher-ranked chunk, **When** the Orchestrator scores compressibility, **Then** its `compressibility_score` is above 0.7 (configurable threshold).
2. **Given** a high-relevance, unique chunk, **When** the Orchestrator scores compressibility, **Then** its `compressibility_score` is below 0.3.
3. **Given** no budget pressure signal, **When** the Orchestrator runs, **Then** compressibility scores are still computed and attached (they are advisory metadata, not conditional).

---

### User Story 5 — Normalized Evidence Pack Output Contract (Priority: P1)

The Orchestrator always emits a fully normalized Evidence Pack whose schema is stable and consumable by the Context Builder (012) without further transformation: each Evidence Item includes document ID, section/hierarchy path, entity/relation tags, citation object, raw text, and final relevance score.

**Why this priority**: The Evidence Pack is the interface contract between 011 and 012; schema instability would break all downstream consumers.

**Independent Test**: Run the full orchestration pipeline end-to-end with synthetic inputs. Assert that the returned `EvidencePack` object validates against the defined schema with all mandatory fields present and correctly typed.

**Acceptance Scenarios**:

1. **Given** a valid Retrieval Plan output fed to the Orchestrator, **When** orchestration completes, **Then** `EvidencePack.items` is a non-empty list of `EvidenceItem` objects, each with non-null `doc_id`, `text`, `relevance_score`, `sources`, and `citation`.
2. **Given** retrieval results from a single strategy only, **When** packaged, **Then** `EvidencePack` still conforms to the full schema with single-source attribution.
3. **Given** an empty retrieval result set (no hits from any strategy), **When** packaged, **Then** `EvidencePack.items` is an empty list and `EvidencePack.is_empty` is `True`; no error is raised.

---

### Edge Cases

- What happens when all retrieval strategies return zero results? → Evidence Pack emitted with empty items list and `is_empty=True`; no exception propagated.
- What happens when the embedding service used for near-duplicate detection is unavailable? → Orchestrator falls back to exact-match-only deduplication and logs a structured warning; pipeline continues.
- What happens when chunk lineage links (prev/next/parent) point to chunks not present in retrieval results? → Expansion stage fetches adjacent chunks via the `IEvidenceExpander` contract; if fetch fails, the original chunk is kept without expansion.
- What happens when all chunks from one strategy are duplicates of another strategy's results? → All duplicates merged; the surviving Evidence Pack may have fewer items than either strategy alone — this is correct behaviour.
- What happens when `compressibility_score` computation fails for one item? → Fallback to `compressibility_score=0.5` (neutral) for that item; error logged with item id; remaining items unaffected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept raw retrieval results from one or more strategies, each tagged with strategy identifier and retrieval score.
- **FR-002**: The system MUST detect and merge exact-match duplicates across strategies, retaining the highest score and combining source references.
- **FR-003**: The system MUST detect near-duplicate chunks via embedding similarity and apply deduplication when similarity exceeds a configurable threshold (default 0.95).
- **FR-004**: The system MUST optionally expand high-relevance truncated chunks with adjacent context using chunk lineage links, controlled by a configurable relevance threshold.
- **FR-005**: The system MUST compute a `compressibility_score` (0.0–1.0) for each surviving Evidence Item and attach it as advisory metadata.
- **FR-006**: The system MUST rank surviving Evidence Items by a fused score combining retrieval score, entity/relation relevance (from 008), and optional recency/authority metadata.
- **FR-007**: The system MUST emit a normalized `EvidencePack` containing a list of `EvidenceItem` objects, each carrying: `doc_id`, `section_path`, `entity_tags`, `relation_tags`, `citation`, `text`, `relevance_score`, `compressibility_score`, and `sources`.
- **FR-008**: The system MUST expose pluggable interfaces for each pipeline stage: `IEvidenceCollector`, `IDeduplicator`, `IEvidenceExpander`, `IEvidencePrioritizer`.
- **FR-009**: The system MUST handle empty retrieval inputs gracefully, returning an `EvidencePack` with `is_empty=True` and an empty items list.
- **FR-010**: The system MUST NOT perform prompt construction, token budgeting, answer generation, or retrieval execution.
- **FR-011**: The system MUST NOT contain domain-specific logic; all domain behaviour MUST be injected via configuration or interface implementations.
- **FR-012**: The system MUST emit structured log entries at each pipeline stage boundary, including item counts before and after each stage and elapsed time.
- **FR-013**: The system MUST record a `token_reduction_ratio` on the `EvidencePack` representing the estimated token count of the pack vs. the total raw retrieval output, enabling measurable compression validation.

### Key Entities

- **`EvidencePack`**: Top-level output container; holds the ordered list of `EvidenceItem`s, metadata (query id, strategy sources used, `is_empty`, `token_reduction_ratio`, pipeline trace).
- **`EvidenceItem`**: Single unit of evidence; carries `doc_id`, `section_path`, `entity_tags`, `relation_tags`, `citation`, `text`, `relevance_score`, `compressibility_score`, `sources` (list of strategy + score pairs).
- **`Citation`**: Structured attribution object; includes document id, chunk id, score, and excerpt metadata (page, section, timestamp if available).
- **`RetrievalStrategyResult`**: Input DTO; raw results from one retrieval strategy; carries strategy identifier, list of raw chunks with scores.
- **`ChunkLineage`**: Reference structure describing parent/child/prev/next relationships from spec 007; used by the expander stage.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture layer boundaries; no infrastructure imports in domain/application layers.
- **NFR-002**: All I/O-bound operations (embedding similarity calls, adjacent chunk fetches) MUST be async; public APIs MUST include type hints.
- **NFR-003**: External providers (embedding model for dedup, chunk store for expansion) MUST be swappable via the existing factory interfaces.
- **NFR-004**: The Evidence Orchestrator MUST attach source citations to every `EvidenceItem` for downstream RAG auditability (spec VI).
- **NFR-005**: Unit and integration tests MUST cover deduplication logic, prioritization fusion, expansion gate, compressibility scoring, and the full pipeline end-to-end.
- **NFR-006**: Structured logging MUST include `request_id`, `query_id`, stage name, item counts, and latency at every stage boundary.
- **NFR-007**: Secrets (embedding API keys, chunk store credentials) MUST NOT appear in source control.
- **NFR-008**: The `EvidencePack` schema MUST be versioned (`schema_version` field) to allow non-breaking evolution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a query whose retrieval results contain ≥ 20% duplicate chunks (by exact or near-duplicate match), the Evidence Pack's item count is at least 20% lower than the raw input count — verifiable against the golden query set from spec 014 (Answer Quality).
- **SC-002**: The `token_reduction_ratio` on every non-empty Evidence Pack is ≤ 0.85 (i.e., at least a 15% token reduction vs. raw retrieval output) when duplicates are present; validated by automated test against the golden query set from spec 014 (Answer Quality).
- **SC-003**: Every `EvidenceItem` in every Evidence Pack produced by the pipeline carries all mandatory schema fields with correct types — zero schema validation failures in unit or integration test runs.
- **SC-004**: The full orchestration pipeline (collect → deduplicate → expand → compress-flag → prioritize → package) completes within an acceptable latency bound for a result set of up to 100 raw chunks — a concrete target (indicatively under 500 ms) will be established after baseline measurement on reference hardware during the planning phase; this criterion is a performance intention, not a hard gate for initial delivery.
- **SC-005**: Source attribution is 100% accurate: every `EvidenceItem.sources` list correctly reflects all retrieval strategies that contributed the chunk — verifiable by comparing against synthetic known-attribution test fixtures.
- **SC-006**: Orchestrator correctness is configurable without code changes: dedup threshold, expansion threshold, compressibility threshold, and fusion weights are all settable via field-pack YAML config (generic < domain < project precedence, per spec 002).

## Assumptions

- Specs 009 (Retrieval Plan) and 010 (Retrieval Engine V2) have stable output contracts; the Evidence Orchestrator consumes `RetrievalStrategyResult` objects whose schema is defined in 010.
- Specs 007 (Intelligent Chunking) and 008 (Knowledge Representation) expose stable lineage and entity/relation tag interfaces; actual data may be populated lazily.
- Embedding similarity for near-duplicate detection reuses the embedding provider already registered via `LLMProviderFactory`; no new provider type is required.
- Adjacent chunk expansion fetches from the same chunk store used by retrieval; a lightweight read interface is sufficient (no write operations).
- Token counting for `token_reduction_ratio` uses a configurable tokenizer consistent with the LLM provider in use; defaults to a character-based approximation when no tokenizer is configured.
- The Evidence Orchestrator runs synchronously within the request-handling pipeline for latency-sensitive queries; Celery offload is not required unless the result set exceeds a configurable size threshold (default: 500 raw chunks).
- Domain-specific fusion weight overrides (e.g., pharmacy entity boost) are supplied via field-pack YAML under the `evidence_orchestrator` namespace; no code changes needed for new domains.
