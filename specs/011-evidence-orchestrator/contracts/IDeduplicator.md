# Contract: `IDeduplicator`

**Module**: `src/core/evidence_orchestrator/interfaces.py`
**Stage**: Deduplicate (stage 2 of 6)

## Purpose

Detects and merges duplicate and near-duplicate `CollectedItem` objects, producing
a deduplicated list where each unique content chunk appears at most once with merged
source attribution and the highest score retained.

## Protocol Definition

```python
class IDeduplicator(ABC):
    @abstractmethod
    async def deduplicate(
        self,
        items: list[CollectedItem],
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]: ...
```

## Behaviour Contract

| Condition | Expected Behaviour |
|-----------|-------------------|
| Two items share the same `chunk_id` (exact duplicate) | Merge: keep highest `candidate.score`; union their source strategy lists; drop the lower-scoring item |
| Two items have `content_excerpt` cosine similarity ≥ `config.dedup_similarity_threshold` | Merge using same merge rule as exact duplicates |
| `config.dedup_near_enabled = False` | Skip near-duplicate pass entirely; exact-match pass still runs |
| `len(items) > config.dedup_near_batch_limit` | Replace cosine-similarity pass with character n-gram Jaccard (n=3); log structured warning with item count |
| Embedding provider unavailable during near-dup pass | Fall back to character n-gram Jaccard; log structured warning; pipeline continues |
| All items are unique | Return input list unchanged |
| Input is empty | Return `[]` |

## Merge Rule (canonical)

When merging item A and item B (A has higher score):
- `chunk_id` = A's chunk_id
- `candidate.score` = max(A.score, B.score)
- `strategy_id` = A's strategy_id (primary)
- Merged `sources` list (constructed by pack assembler from lineage) includes both A and B strategies

## Output

`list[CollectedItem]` — deduplicated; order is score-descending within merged groups,
preserving relative rank of non-merged items.

## Concrete Implementation

`src/core/evidence_orchestrator/deduplication/embedding_deduplicator.py`
→ `EmbeddingDeduplicator`

Uses `LLMProviderFactory` embedding provider for batch cosine similarity.

## Observability

Log: `stage="deduplicate"`, `input_count`, `output_count` (= input - merged),
`duplicates_merged`, `method_used` ("exact_only" | "embedding" | "character_ngram"),
`latency_ms`.
