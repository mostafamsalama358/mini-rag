# Research: Context Builder (spec 012)

**Date**: 2026-07-14
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## Decision 1: Conflict Detection Algorithm

**Question**: How does `IConflictDetector` derive `entity_id` and `attribute` from
`EvidenceItem` fields without an upstream schema change to spec 011?

**Decision**: Use `EvidenceItem.entity_tags` (list[str] — canonical entity forms
populated by Evidence Orchestrator from spec 008 KnowledgeUnit tags) as the grouping
key. Two items that share one or more entity tags are candidate conflict pairs. To
determine whether a conflict exists, apply a numeric-value heuristic: extract all
numeric tokens from `EvidenceItem.text` that appear within a configurable character
window of a matched entity tag mention; if two items share an entity tag but their
associated numeric values differ by more than a configurable tolerance, a `ConflictGroup`
is emitted. The `attribute` field in `ConflictGroup` is set to the matched entity tag
string (e.g., `"metformin"`, `"price_usd"`). Non-numeric conflicts (e.g., two items
citing different category labels for the same entity) are detected by a second pass that
checks for mutually exclusive boolean or categorical patterns within a window.

**Rationale**: `entity_tags: list[str]` already carries canonical entity identifiers from
spec 008; no upstream schema extension is needed. The heuristic covers the primary
conflict patterns in RAG corpora (dosage disagreement, price disagreement, date
disagreement). False positives are tolerable — they surface in `Context.conflicts` as
advisory metadata; Answer Generation decides whether to disclose or ignore.

**Alternatives considered**:
- *Require a structured attribute-value schema on `EvidenceItem`*: Rejected — requires
  a breaking change to spec 011 EvidencePack and blocks 012 delivery on an unplanned
  upstream change.
- *LLM-based conflict detection*: Rejected for v1 — adds latency and non-determinism;
  makes unit testing impossible without live LLM. Reserved for a future optional
  `IConflictDetector` implementation.
- *Embedding-based semantic contradiction detection*: Rejected for v1 — same latency
  and dependency concerns as LLM; and embeddings are not stored on `EvidenceItem`.

---

## Decision 2: Compression Strategy (Default)

**Question**: Should the default `IContextCompressor` use LLM summarization or a
heuristic approach? What heuristic?

**Decision**: Heuristic sentence-boundary truncation is the default. The compressor
splits the item text on sentence boundaries (`.`, `?`, `!` followed by whitespace),
then greedily appends sentences until the target token count is reached. The last
complete sentence fitting the budget is kept; partial sentences are discarded. This
preserves grammatical coherence without an LLM call.

A `LLMContextCompressor` is a secondary optional implementation behind `IContextCompressor`
— it calls the existing `LLMProviderFactory` to summarize the text to a target length.
It is not required for initial delivery.

**Rationale**: Keeping the hot path free of LLM calls satisfies the ≤ 150 ms p95
performance goal (SC-005). Sentence-boundary truncation is deterministic, fully unit-
testable, and produces acceptable quality for most evidence snippets. The pluggable
interface means the LLM compressor can be swapped in per field-pack config.

**Alternatives considered**:
- *LLM summarization as default*: Rejected — doubles latency on every compressed item;
  makes unit tests non-deterministic; requires a live LLM in CI.
- *Hard character truncation*: Rejected — produces mid-sentence cuts that confuse the
  LLM reading the context.
- *Extractive sentence scoring (TF-IDF)*: Considered as an enhancement over raw
  sentence-boundary truncation; deferred to a future `ExtractiveSentenceCompressor`
  implementation.

---

## Decision 3: Final-Pass Deduplication Algorithm

**Question**: `EvidenceItem` does not carry embeddings. How can the final-pass
deduplicator compute similarity without re-embedding (expensive) or ignoring text
similarity altogether?

**Decision**: Reuse the existing `char_ngrams` and `jaccard_similarity` helpers from
`src/core/evidence_orchestrator/text_similarity.py`. Compute 3-gram Jaccard similarity
between pairs of surviving items. Default threshold: **0.85** (lower than Evidence
Orchestrator's embedding-cosine threshold of 0.95 — different metric but deliberately
conservative to avoid over-deduplication). When similarity ≥ threshold, drop the
lower-ranked item (by `relevance_score`).

This is O(n²) over surviving items. For typical inputs (10–50 items post-selection)
the cost is negligible. A configurable `final_dedup_max_pairs` cap (default 2000)
prevents pathological runtime on unusually large inputs.

An optional embedding-based path is reserved for future implementation via
`IEmbeddingProvider` (already defined in `evidence_orchestrator/interfaces.py`).

**Rationale**: The text_similarity module is already present and battle-tested. Char
n-gram Jaccard works well for near-verbatim duplicates (the primary use case — same
paragraph retrieved twice). No new dependencies. Keeps the component self-contained.

**Alternatives considered**:
- *Re-embed items using IEmbeddingProvider*: Rejected as default — adds async embedding
  call and significant latency; reserved as optional upgrade path.
- *Skip final dedup entirely*: Rejected — spec explicitly requires it as a safety net
  (FR-007); Evidence Orchestrator may not catch all duplicates at its threshold.
- *MinHash LSH*: Over-engineered for 10–50 items; reserved if scale increases.

---

## Decision 4: Token Counter Reuse

**Question**: Should Context Builder define its own token counter or reuse spec 011's?

**Decision**: Reuse `ITokenCounter` (interface) and `CharacterApproximationTokenCounter`
/ `TiktokenTokenCounter` (implementations) directly from
`src/core/evidence_orchestrator/`. No copy; import directly.

**Rationale**: The token counter is a pure utility with no domain logic. Duplicating it
would create two sources of truth for the same approximation. The existing interface is
clean and already injectable.

**Alternatives considered**:
- *Define a new `IContextTokenCounter` interface*: Rejected — identical signature, zero
  benefit, adds import indirection.

---

## Decision 5: Stitching Sort Order

**Question**: `EvidenceItem.section_path` is `list[str]` (heading path), not a flat
string. How should `IContextStitcher` sort by it?

**Decision**: Sort surviving items by `(document_id, section_path, -relevance_score)` —
where `section_path` comparison is lexicographic on the list (Python's default
list-of-strings comparison, which sorts by depth and then alphabetically within each
level). Items with an empty `section_path` (`[]`) sort after items with a non-empty
path within the same document. Items with no `document_id` are grouped at the end.

**Rationale**: This produces document-coherent ordering: all sections from document A
appear before document B, sections appear in heading order within a document, and within
the same section the higher-relevance item leads. This is deterministic and requires no
additional metadata.

**Alternatives considered**:
- *Sort by relevance score only*: Rejected — produces the disconnected-fragment problem
  the spec explicitly targets.
- *Cluster by semantic similarity*: Rejected — adds embedding calls and non-determinism.

---

## Decision 6: `EvidencePack` Schema Version Check

**Question**: Should Context Builder validate `EvidencePack.schema_version` at runtime?

**Decision**: Yes. On pipeline entry, check that the major version of
`EvidencePack.schema_version` matches the expected `"1"`. If it does not, raise
`EvidencePackVersionError` (a subclass of `ContextBuildError`). Minor and patch version
differences are accepted (backwards-compatible by spec 011 versioning policy).

**Rationale**: Prevents silent data-corruption bugs when spec 011 cuts a breaking change.
The check is a single string comparison with negligible overhead.

---

## Decision 7: `section_path` Type in `ContextBlock`

**Question**: The spec defines `ContextBlock.section_path: str | None` but
`EvidenceItem.section_path` is `list[str]`. How are they reconciled?

**Decision**: `ContextBlock.section_path` stores the joined heading path as a single
`/`-delimited string (e.g., `["Introduction", "Background"] → "Introduction/Background"`).
Empty list maps to `None`. This gives downstream Answer Generation (013) a flat,
human-readable section label without requiring it to handle list types.

**Rationale**: The `Context` output contract is defined by this spec; choosing a flat
string for `ContextBlock.section_path` simplifies 013's rendering logic. The mapping is
lossless — the original list is not needed downstream.

---

## Decision 8: Configuration File Location and Format

**Decision**: Field-pack YAML at `src/fields/generic/context_builder.yaml` (generic
baseline), overridable by `src/fields/pharmacy/context_builder.yaml` and
`src/fields/legal/context_builder.yaml`. Config loading follows the same
`load_config_from_yaml` / `merge_config` pattern established in spec 011.

**Rationale**: Consistent with all other field-pack configs; uses the existing
`FieldRegistry` resolution stack (generic < domain < project, per spec 002).
