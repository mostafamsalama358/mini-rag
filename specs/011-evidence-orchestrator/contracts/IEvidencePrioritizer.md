# Contract: `IEvidencePrioritizer`

**Module**: `src/core/evidence_orchestrator/interfaces.py`
**Stage**: Prioritize (stage 5 of 6, after compress-flag)

## Purpose

Ranks `EvidenceItem` objects by computing a `relevance_score` that fuses:
1. Normalized retrieval score (from spec 010 output)
2. Entity-match ratio (resolved entities from `RetrievalPlan` found in item text)
3. Recency/authority score (from `SourceRef` metadata if available)

The Prioritizer operates on `EvidenceItem` objects (post-dedup, post-expand,
post-compress-flag), setting their final `relevance_score` and returning them
in descending order.

## Protocol Definition

```python
class IEvidencePrioritizer(ABC):
    @abstractmethod
    async def prioritize(
        self,
        items: list[EvidenceItem],
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> list[EvidenceItem]: ...
```

## Fusion Formula

```
final_score = clamp(
    w_ret × norm(retrieval_score)
  + w_ent × entity_match_ratio
  + w_rec × recency_score,
  0.0, 1.0
)
```

Where:
- `norm(retrieval_score)` = min-max normalization across all items; if all scores equal,
  normalized score = 1.0 for all.
- `entity_match_ratio` = count of `plan.entities` whose `canonical_form` appears
  (case-insensitive substring) in `item.text`, divided by `max(1, len(plan.entities))`,
  capped at 1.0.
- `recency_score` = derived from `source_ref` timestamp if present (normalized to [0,1]
  across item set, most-recent = 1.0); 0.5 neutral when absent.
- Weights from `config.fusion_weights` (default: ret=0.6, ent=0.3, rec=0.1).

## Behaviour Contract

| Condition | Expected Behaviour |
|-----------|-------------------|
| `plan.entities` is empty | `entity_match_ratio = 0.0` for all items; weights re-normalize automatically (retrieval and recency carry the full score) |
| All items have identical retrieval scores | All `norm(retrieval_score) = 1.0`; entity + recency signals differentiate |
| No items have recency metadata | `recency_score = 0.5` (neutral) for all items |
| Single item in list | Returns list with that item; score computed normally |
| Input is empty | Return `[]` |

## Side Effects

- Sets `item.relevance_score` and `item.entity_tags` (list of matched canonical forms).
- Returns items sorted descending by `relevance_score`.

## Output

`list[EvidenceItem]` — same items, updated `relevance_score` and `entity_tags`, sorted
descending.

## Concrete Implementation

`src/core/evidence_orchestrator/prioritization/fusion_prioritizer.py`
→ `FusionPrioritizer`

## Observability

Log: `stage="prioritize"`, `input_count`, `output_count`,
`entity_matches_total`, `recency_signals_present`, `latency_ms`.
