# Contract: `EvidencePack` — Output Schema

**Module**: `src/core/evidence_orchestrator/models.py`
**Schema version**: `1.0.0`
**Consumer**: spec 012 (Context Builder)

## Purpose

`EvidencePack` is the stable public output contract of the Evidence Orchestrator.
It carries a ranked, deduplicated list of `EvidenceItem` objects plus pipeline metadata.
Spec 012 (Context Builder) consumes `EvidencePack` directly with no transformation.

## Schema

```
EvidencePack
├── pack_id: str                  # "ep_" + sha256(plan_id + created_at)[:16]
├── plan_id: str                  # from RetrievalPlan.plan_id (non-empty)
├── schema_version: str           # "1.0.0" — pinned; bump on breaking change
├── items: list[EvidenceItem]     # ordered descending by relevance_score
├── is_empty: bool                # True iff len(items) == 0 (enforced by validator)
├── strategies_used: list[str]    # from RetrievalResult.metadata.executed_strategies
├── token_reduction_ratio: float | None
│                                 # pack_tokens / raw_input_tokens
│                                 # None when token counting not possible
│                                 # Capped at 1.0 if expansion increased total tokens
├── raw_candidate_count: int      # len(RetrievalResult.candidates) before dedup
├── trace: OrchestratorTrace      # full pipeline trace (see data-model.md)
└── created_at: str               # ISO 8601 UTC, e.g. "2026-07-14T13:05:00Z"

EvidenceItem
├── item_id: str                  # "ei_" + sha256(chunk_id + doc_id)[:16]
├── doc_id: str                   # non-empty
├── chunk_id: str                 # non-empty
├── section_path: list[str]       # heading path; [] if not available
├── entity_tags: list[str]        # canonical forms of matched plan entities
├── relation_tags: list[str]      # relation types from spec 008; [] if not available
├── citation: Citation            # always present (non-null)
├── text: str                     # non-empty; optionally expanded
├── relevance_score: float        # ∈ [0.0, 1.0]
├── compressibility_score: float  # ∈ [0.0, 1.0]; advisory for spec 012
├── sources: list[EvidenceItemSource]  # non-empty; one per contributing strategy
└── expanded: bool                # True if adjacent context was prepended/appended

Citation
├── document_id: str              # non-empty
├── chunk_id: str                 # non-empty
├── retrieval_score: float        # ≥ 0.0
├── score_source: str             # "reranker" | "fusion" | "raw"
├── page_number: int | None
├── section_title: str | None
├── document_title: str | None
└── chunk_index: int | None

EvidenceItemSource
├── strategy_id: str              # e.g. "semantic", "keyword"
└── raw_score: float
```

## Invariants

1. `is_empty == (len(items) == 0)` — enforced by Pydantic model validator; construction
   with inconsistent value raises `ValidationError`.
2. `items` is always sorted descending by `relevance_score` when produced by
   `FusionPrioritizer`.
3. `token_reduction_ratio`, if present, satisfies `0.0 < ratio ≤ 1.0`.
4. Every `EvidenceItem.citation` is non-null.
5. Every `EvidenceItem.sources` is non-empty.
6. No two items in `items` share the same `chunk_id` (enforced by deduplication stage).

## Empty-Result Guarantee

When no retrieval results are available, the Orchestrator returns:

```python
EvidencePack(
    pack_id="ep_...",
    plan_id=plan.plan_id,
    schema_version="1.0.0",
    items=[],
    is_empty=True,
    strategies_used=[],
    token_reduction_ratio=None,
    raw_candidate_count=0,
    trace=OrchestratorTrace(...),
    created_at="...",
)
```

No exception is raised; the caller (spec 012) checks `is_empty` before proceeding.

## Versioning Policy

- **PATCH** (1.0.x): field description / docstring changes only.
- **MINOR** (1.x.0): new optional fields added; backwards-compatible.
- **MAJOR** (x.0.0): existing field removed or type changed; requires migration.
- `schema_version` is checked by spec 012 at runtime; incompatible major version
  must raise `EvidencePackVersionError`.
