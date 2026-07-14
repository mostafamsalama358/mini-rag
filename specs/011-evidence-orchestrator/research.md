# Research: Evidence Orchestrator (011)

**Branch**: `011-evidence-orchestrator` | **Date**: 2026-07-14

## D1 — Input Contract: What does the Orchestrator consume from spec 010?

**Decision**: The primary input is `RetrievalResult` (from `src/core/retrieval_engine/models.py`),
which carries `candidates: tuple[RetrievedCandidate, ...]`. Each `RetrievedCandidate` has
`chunk_id`, `document_id`, `score`, `score_source`, `source_ref: SourceRef | None`, and
`content_excerpt: str`. The `RetrievalPlan` (spec 009) is passed alongside so the Orchestrator
can access `plan.entities` (resolved entities for relevance fusion) and `plan.filters`.

**Rationale**: Both `RetrievalResult` and `RetrievalPlan` are frozen Pydantic models with
`schema_version = "1.0.0"`. No DTO translation layer is needed. The Orchestrator wraps
`RetrievedCandidate` objects into its own `EvidenceItem` during the Collect stage, decoupling
its internal model from the retrieval engine's.

**Alternatives considered**:
- Accepting a list of raw `RawCandidate` objects pre-fusion: rejected — the Orchestrator
  should receive the fused, reranked output of 010, not raw per-strategy hits.
- Defining a new `RetrievalStrategyResult` DTO for the boundary: deferred — the existing
  `RetrievedCandidate` carries sufficient attribution; per-strategy grouping is preserved
  via `retriever_id` on `RawCandidate` (pre-fusion) and can be reconstructed from
  `RetrievalTrace.steps` if needed.

---

## D2 — Near-Duplicate Detection: Embedding vs. Heuristic

**Decision**: Two-pass deduplication:
1. **Exact-match pass** (O(n)): hash `chunk_id`; merge any pair with the same `chunk_id`
   across strategies immediately. This covers 100% of retriever-level duplicates.
2. **Near-duplicate pass** (O(n²) cosine, bounded): batch-embed `content_excerpt` for
   surviving chunks using the existing `LLMProviderFactory` embedding provider (same
   provider already used for dense retrieval). Compute cosine similarity matrix; merge
   pairs above the configured threshold (default 0.95). For sets larger than
   `dedup_near_batch_limit` (default 200), fall back to character n-gram Jaccard
   similarity to avoid latency blowout.

**Rationale**: Re-embedding a post-dedup set of ≤100 chunks is one extra batch embedding
call with negligible latency cost (same model already warm in process). Cosine similarity
on normalized vectors is the most reliable signal for semantic near-duplicates. The
configurable fallback protects large-set performance without requiring a new provider.

**Alternatives considered**:
- Require retrieval engine to attach embedding vectors to `RetrievedCandidate`: rejected —
  that would bloat the spec 010 contract and tightly couple the retrieval result schema
  to downstream consumers.
- MinHash / LSH for approximate near-dedup at scale: deferred to a future optimization
  phase; correct behavior at ≤100 chunks is the current scope.

---

## D3 — Adjacent Chunk Expansion: Access Pattern

**Decision**: Define a thin `IChunkReader` interface (read-only) with a single
`async def get_chunk(chunk_id: str, document_id: str) -> Chunk | None` method.
The `IEvidenceExpander` receives this as a dependency. The concrete implementation
in infrastructure delegates to `ChunkRepository` (already exists at
`src/repositories/chunk_repository.py`). Expansion is triggered only when:
- `chunk.score >= expansion_threshold` (configurable, default 0.80), AND
- `chunk.relationships.previous_chunk_id` or `next_chunk_id` is non-null, AND
- expansion is not globally disabled via config.

Adjacent text is prepended (prev) or appended (next) to the Evidence Item's `text`
field; the adjacent chunk is not emitted as a separate Evidence Item.

**Rationale**: Reusing `ChunkRepository` via a thin interface keeps the Orchestrator
domain-layer pure (no direct repository import). The expansion gate ensures we only
pay the extra read cost for genuinely high-signal chunks.

**Alternatives considered**:
- Fetch parent chunk (not prev/next): both are supported; parent is tried first
  if `relationships.parent_chunk_id` is set and the chunk text is shorter than
  `expansion_min_chars` (default 150), to handle heading-only chunks.
- Eagerly expand all top-N chunks: rejected — expansion is a "last-mile" quality
  improvement, not a bulk operation. Budget should be spent where needed.

---

## D4 — Compressibility Scoring: Method

**Decision**: A lightweight, CPU-only heuristic in three steps:
1. **Redundancy score**: character n-gram (n=3) Jaccard similarity between this item's
   text and the union of all higher-ranked items' texts. High overlap → high
   compressibility.
2. **Relevance inverse**: `1 - normalized_relevance_score`. Low-relevance items are
   more compressible regardless of overlap.
3. **Final score**: `0.6 × redundancy + 0.4 × relevance_inverse`, clamped to [0, 1].
   Weights are configurable via field-pack YAML under `compressibility_weights`.

**Rationale**: No LLM call required; deterministic; fast (O(n²) character ops for ≤100
chunks is negligible). The score is advisory metadata for spec 012 — precision matters
less than direction. The two-factor formula gives 012 a signal that captures both
duplicate-of-better-item and genuinely-low-value content.

**Alternatives considered**:
- LLM-based summarizability scoring: rejected — this is spec 012's responsibility;
  the Orchestrator must not perform prompt construction.
- Embedding cosine similarity against the query for relevance inverse: would require
  another embedding call; character-level relevance score from the fusion step is
  sufficient for flagging.

---

## D5 — Relevance Fusion Scoring: Formula

**Decision**: Weighted linear fusion:

```
final_score = w_ret × norm(retrieval_score)
            + w_ent × entity_match_ratio
            + w_rec × recency_score
```

Where:
- `norm(retrieval_score)` = min-max normalized across all items in the pack.
- `entity_match_ratio` = count of `RetrievalPlan.entities` whose `canonical_form`
  appears (case-insensitive substring) in the item's text, divided by
  `max(1, len(plan.entities))`. Capped at 1.0.
- `recency_score` = derived from `SourceRef` metadata (document timestamp if present;
  0.5 neutral otherwise). Normalized to [0, 1] across the item set.
- Default weights: `w_ret=0.6, w_ent=0.3, w_rec=0.1`. Configurable per domain via
  field-pack YAML under `fusion_weights`.

**Rationale**: Simple, transparent, debuggable formula. Entity matching is intentionally
lightweight (substring) to avoid requiring a running NER model at inference time.
Recency is a minor factor but can be boosted in time-sensitive domains (e.g., legal,
regulatory) via domain field-pack override.

**Alternatives considered**:
- RRF (Reciprocal Rank Fusion) of retrieval rank + entity rank: considered, but RRF
  discards absolute score magnitudes; the retrieval engine already applied RRF
  internally; a second RRF at this stage would double-discount differences.
- Neural reranking here: rejected — the retrieval engine already applies reranking (010);
  double-reranking adds latency and is the Orchestrator's non-goal.

---

## D6 — EvidencePack Token Reduction Ratio: Tokenizer

**Decision**: Use a configurable `ITokenCounter` interface with two implementations:
1. `CharacterApproximationTokenCounter`: `ceil(char_count / 4.0)` — always available,
   no dependencies.
2. `TiktokenTokenCounter`: uses `tiktoken` (already a transitive dep via OpenAI
   provider); selectable via config when provider is OpenAI-compatible.

`token_reduction_ratio = pack_token_count / raw_input_token_count`.
`raw_input_token_count` is computed on the full `content_excerpt` of all candidates
in the original `RetrievalResult` before any deduplication.

**Rationale**: The ratio must be computable without knowing which LLM will consume the
pack. The character approximation is "good enough" for the SC-002 validation criterion
(15% reduction threshold); exact counting is a configuration upgrade.

---

## D7 — Module Location & Naming

**Decision**: New module at `src/core/evidence_orchestrator/`, mirroring the
`src/core/retrieval_engine/` structure established by spec 010. Field-pack config
at `src/fields/generic/evidence_orchestrator.yaml` (and domain overrides in
`src/fields/pharmacy/evidence_orchestrator.yaml`, etc.). Tests at
`tests/unit/core/evidence_orchestrator/` and `tests/integration/test_evidence_orchestrator_e2e.py`.

**Rationale**: Consistent with the established `src/core/<feature>/` layering pattern.
The Orchestrator is a pure core module with no FastAPI route dependency; it will be
wired into the RAG service by spec 012 (Context Builder) or a future integration layer.

---

## D8 — Celery Offload Threshold

**Decision**: The Orchestrator runs synchronously (in-process async) by default.
A configurable `celery_offload_threshold` (default: 500 raw candidates) triggers
Celery task submission for unusually large result sets. The async orchestration
pipeline already handles the common case efficiently; Celery is a safety valve only.

**Rationale**: Matches spec assumptions; 100-candidate sets complete well within
the indicative 500 ms target in-process. Celery adds overhead (serialization +
broker round-trip) that is only justified at scale.

---

## D9 — SC-004 Baseline Measurement Plan

**Decision**: During implementation, add a `@pytest.mark.benchmark` integration test
using `pytest-benchmark` that runs the full pipeline on a synthetic 100-item result
set (no external dependencies — mock embeddings and chunk store). The measured p50
latency establishes the official baseline. The plan documents 500 ms as an indicative
ceiling; actual gate is set after the first benchmark run.

**Rationale**: Aligns with SC-004's wording ("pending baseline measurement"). Prevents
premature optimization before we have real numbers.
