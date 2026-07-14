# Data Model: Evidence Orchestrator (011)

**Module**: `src/core/evidence_orchestrator/models.py`

All models are frozen Pydantic `BaseModel` instances unless noted.
No new database tables are introduced by this feature.

---

## Input Models (consumed from upstream specs)

These are defined in upstream specs and consumed as-is; listed here for reference only.

### `RetrievalResult` (spec 010 — `src/core/retrieval_engine/models.py`)
Consumed directly. Key fields used by the Orchestrator:
- `plan_id: str` — passed through to `EvidencePack`
- `candidates: tuple[RetrievedCandidate, ...]` — primary input to Collect stage
- `metadata.executed_strategies: tuple[str, ...]` — recorded in `EvidencePack`

### `RetrievedCandidate` (spec 010 — `src/core/retrieval_engine/models.py`)
- `chunk_id: str`
- `document_id: str`
- `score: float` — fused/reranked score from 010
- `score_source: Literal["reranker", "fusion", "raw"]`
- `source_ref: SourceRef | None` — document/section metadata
- `content_excerpt: str` — text content (may be truncated)
- `rank: int` — rank within 010 output

### `RetrievalPlan` (spec 009 — `src/core/retrieval_planner/models.py`)
Key fields used:
- `plan_id: str`
- `entities: tuple[ResolvedEntity, ...]` — for entity-match fusion scoring
- `retrieval_strategies: tuple[str, ...]` — recorded in `EvidencePack`
- `retrieval_constraints.citation_required: bool`

### `Chunk` / `ChunkRelationships` (spec 007 — `src/core/chunking/models.py`)
Used by Expansion stage via `IChunkReader`:
- `relationships.parent_chunk_id: str | None`
- `relationships.previous_chunk_id: str | None`
- `relationships.next_chunk_id: str | None`
- `text: str`

---

## Internal / Intermediate Model

### `CollectedItem`
Produced by the Collect stage; wraps a `RetrievedCandidate` with Orchestrator-internal
tracking fields before any processing.

```
CollectedItem (frozen)
├── candidate: RetrievedCandidate       # original 010 output
├── strategy_id: str                    # retriever_id from trace
└── raw_token_count: int                # pre-dedup token estimate (ITokenCounter)
```

---

## Output Models

### `Citation`
Structured attribution object carried by every `EvidenceItem`.

```
Citation (frozen)
├── document_id: str                    # non-null
├── chunk_id: str                       # non-null
├── retrieval_score: float              # score from spec 010 output
├── score_source: str                   # "reranker" | "fusion" | "raw"
├── page_number: int | None
├── section_title: str | None
├── document_title: str | None
└── chunk_index: int | None
```

**Validation rules**:
- `document_id` and `chunk_id` must be non-empty strings.
- `retrieval_score` must be ≥ 0.0.

**Constructed from**: `RetrievedCandidate.source_ref` (SourceRef) + `candidate.score`.

---

### `EvidenceItemSource`
Records which retrieval strategy contributed a given chunk (used for merged attribution
when a chunk appeared in multiple strategies).

```
EvidenceItemSource (frozen)
├── strategy_id: str        # e.g. "semantic", "keyword", "metadata"
└── raw_score: float        # score from that strategy before fusion
```

---

### `EvidenceItem`
The primary output unit. Ordered by descending `relevance_score` in `EvidencePack.items`.

```
EvidenceItem (frozen)
├── item_id: str                        # stable hash: sha256(chunk_id + doc_id)[:16]
├── doc_id: str                         # document_id
├── chunk_id: str                       # chunk_id (primary/winning chunk)
├── section_path: list[str]             # heading_path from StructuralContext (may be [])
├── entity_tags: list[str]              # canonical_form of matched ResolvedEntities
├── relation_tags: list[str]            # relation types from spec 008 (may be [])
├── citation: Citation                  # full citation object (always present)
├── text: str                           # deduplicated, optionally expanded content
├── relevance_score: float              # final fused score ∈ [0, 1]
├── compressibility_score: float        # advisory ∈ [0, 1]; 012 uses for compression
├── sources: list[EvidenceItemSource]   # one entry per contributing strategy
└── expanded: bool                      # True if adjacent context was appended
```

**Validation rules**:
- `relevance_score` ∈ [0.0, 1.0].
- `compressibility_score` ∈ [0.0, 1.0].
- `citation` is always non-null (enforced by pack assembler).
- `sources` must be non-empty.
- `text` must be non-empty.

---

### `OrchestratorStageTrace`
Per-stage timing and count metadata embedded in `OrchestratorTrace`.

```
OrchestratorStageTrace (frozen)
├── stage: str              # "collect" | "deduplicate" | "expand" | "compress_flag"
│                           # | "prioritize" | "package"
├── input_count: int
├── output_count: int
└── latency_ms: float
```

---

### `OrchestratorTrace`
Full pipeline trace attached to `EvidencePack` for observability.

```
OrchestratorTrace (frozen)
├── orchestrator_version: str   # e.g. "1.0.0"
├── stages: list[OrchestratorStageTrace]
├── total_latency_ms: float
├── dedup_method_used: str      # "exact_only" | "embedding" | "character_ngram"
└── expansion_enabled: bool
```

---

### `EvidencePack`
Top-level output emitted by the Orchestrator. Consumed directly by spec 012.

```
EvidencePack (frozen)
├── pack_id: str                        # sha256(plan_id + timestamp)[:16], prefix "ep_"
├── plan_id: str                        # from RetrievalPlan.plan_id
├── schema_version: str                 # "1.0.0"
├── items: list[EvidenceItem]           # ordered by descending relevance_score
├── is_empty: bool                      # True iff items is empty
├── strategies_used: list[str]          # from RetrievalResult.metadata.executed_strategies
├── token_reduction_ratio: float | None # pack_tokens / raw_input_tokens; None if uncountable
├── raw_candidate_count: int            # len(RetrievalResult.candidates) before dedup
├── trace: OrchestratorTrace
└── created_at: str                     # ISO 8601 UTC timestamp
```

**Validation rules**:
- `is_empty` must equal `len(items) == 0` (model validator).
- `token_reduction_ratio` if present must be ∈ (0.0, 1.0] — ratio > 1.0 indicates
  expansion added tokens (allowed; capped at 1.0 in that case).
- `schema_version` pinned to `"1.0.0"` in this spec; bumped on breaking changes.

---

## Configuration Model

### `EvidenceOrchestratorConfig`
Loaded from field-pack YAML (`evidence_orchestrator.yaml`); generic < domain < project
precedence (spec 002). Lives in `src/core/evidence_orchestrator/config.py`.

```
EvidenceOrchestratorConfig (extra=forbid)
├── dedup_exact_enabled: bool = True
├── dedup_near_enabled: bool = True
├── dedup_similarity_threshold: float = 0.95          # cosine, ∈ (0, 1]
├── dedup_near_batch_limit: int = 200                  # fallback to char n-gram above
├── expansion_enabled: bool = True
├── expansion_score_threshold: float = 0.80           # min relevance_score to expand
├── expansion_min_chars: int = 150                    # expand if text shorter than this
├── fusion_weights: FusionWeights                     # nested config
├── compressibility_weights: CompressibilityWeights   # nested config
├── token_counter: str = "character"                  # "character" | "tiktoken"
├── celery_offload_threshold: int = 500               # candidates above which → Celery
└── schema_version: str = "1.0.0"

FusionWeights (extra=forbid)
├── retrieval: float = 0.6
├── entity: float = 0.3
└── recency: float = 0.1

CompressibilityWeights (extra=forbid)
├── redundancy: float = 0.6
└── relevance_inverse: float = 0.4
```

**Validation**: `fusion_weights` must sum to 1.0 (± 0.001 tolerance).
`compressibility_weights` must sum to 1.0 (± 0.001 tolerance).

---

## Entity Relationships

```
RetrievalResult ──provides──► [RetrievedCandidate, ...]
                                    │
                            EvidenceOrchestrator.orchestrate()
                                    │
                            CollectedItem (internal)
                                    │ deduplicate / expand / score
                                    ▼
                             EvidenceItem
                                    │ (carries)
                             ├── Citation          (constructed from SourceRef)
                             ├── EvidenceItemSource[] (per contributing strategy)
                             └── text              (optionally expanded via IChunkReader)
                                    │
                              EvidencePack         (final output → spec 012)
                                    │ (carries)
                             └── OrchestratorTrace
                                      └── OrchestratorStageTrace[]
```

---

## No New Database Migrations

The Evidence Orchestrator is a stateless transformation pipeline. It reads from existing
chunk storage (via `IChunkReader → ChunkRepository`) and writes nothing to the database.
No Alembic migrations are required.
