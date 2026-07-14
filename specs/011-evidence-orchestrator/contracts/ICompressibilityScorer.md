# Contract: `ICompressibilityScorer`

**Module**: `src/core/evidence_orchestrator/interfaces.py`
**Stage**: Compress-flag (stage 4 of 6)

## Purpose

Attaches an advisory `compressibility_score` (0.0–1.0) to each `EvidenceItem` after
deduplication and expansion. A high score signals to the Context Builder (spec 012)
that the item is a strong candidate for summarisation or omission under token budget
pressure. The Orchestrator itself performs no compression — it only scores and flags.

## Protocol Definition

```python
class ICompressibilityScorer(ABC):
    @abstractmethod
    async def score(
        self,
        items: list[EvidenceItem],
        config: EvidenceOrchestratorConfig,
    ) -> list[EvidenceItem]: ...
```

## Behaviour Contract

| Condition | Expected Behaviour |
|-----------|-------------------|
| Single item in list | `compressibility_score` computed normally using redundancy=0.0 (no higher-ranked items to compare against) and relevance-inverse from its own `relevance_score`; score reflects only the relevance-inverse component |
| Item's text has high n-gram overlap with union of all higher-ranked items' texts | `redundancy` component is high → elevated `compressibility_score` |
| Item has a high `relevance_score` (close to 1.0) | `relevance_inverse` component is low → reduces `compressibility_score` |
| Item has a low `relevance_score` (close to 0.0) | `relevance_inverse` component is high → elevates `compressibility_score` regardless of uniqueness |
| `compressibility_score` computation fails for one item (e.g. text is empty) | Fallback to `compressibility_score=0.5` (neutral) for that item; log structured error with `item_id`; remaining items unaffected |
| Input is empty | Return `[]` |

## Scoring Formula

```
redundancy(i)     = character_ngram_jaccard(text_i, union(text_j for j ranked above i), n=3)
relevance_inverse = 1.0 - item.relevance_score
compressibility   = clamp(
    config.compressibility_weights.redundancy × redundancy
  + config.compressibility_weights.relevance_inverse × relevance_inverse,
    0.0, 1.0
)
```

Default weights (from `EvidenceOrchestratorConfig.compressibility_weights`):
- `redundancy = 0.6`
- `relevance_inverse = 0.4`

Weights must sum to 1.0 (± 0.001 tolerance); configurable per domain via field-pack
YAML under `compressibility_weights`.

## Side Effects

- Sets `item.compressibility_score` on each `EvidenceItem`.
- Does **not** reorder items or modify any other field.
- Does **not** drop or summarise any item — scoring only.

## Output

`list[EvidenceItem]` — same length and order as input; each item has an updated
`compressibility_score`.

## Concrete Implementation

`src/core/evidence_orchestrator/compression/redundancy_scorer.py`
→ `RedundancyScorer`

CPU-only; no LLM or embedding calls. Character n-gram (n=3) Jaccard similarity
computed over the ordered item list, building a running union of text seen in
higher-ranked items.

## Observability

Log: `stage="compress_flag"`, `input_count`, `output_count` (always equals
`input_count`), `high_compressibility_count` (items with score ≥ 0.7),
`latency_ms`.
