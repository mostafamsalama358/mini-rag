# Contract: `IEvidenceExpander`

**Module**: `src/core/evidence_orchestrator/interfaces.py`
**Stage**: Expand (stage 3 of 6)

## Purpose

For `CollectedItem` objects whose relevance score meets or exceeds the expansion
threshold and whose chunk has adjacent context links (prev/next/parent from spec 007),
fetches and appends the adjacent text. Prevents half-context answers on truncated
high-signal chunks. Adjacent chunks are consumed into the item's text, not emitted as
independent items.

## Protocol Definition

```python
class IEvidenceExpander(ABC):
    @abstractmethod
    async def expand(
        self,
        items: list[CollectedItem],
        chunk_reader: IChunkReader,
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]: ...
```

## Supporting Interface: `IChunkReader`

```python
class IChunkReader(ABC):
    @abstractmethod
    async def get_chunk(
        self,
        chunk_id: str,
        document_id: str,
    ) -> Chunk | None: ...
```

Concrete implementation: delegates to `ChunkRepository` (read-only). Wired at
composition root (not imported directly by Orchestrator core).

## Behaviour Contract

| Condition | Expected Behaviour |
|-----------|-------------------|
| `config.expansion_enabled = False` | Return items unchanged; no reads |
| `item.candidate.score < config.expansion_score_threshold` | Skip item; return unchanged |
| `item.candidate.score >= threshold` AND `len(text) < config.expansion_min_chars` | Try parent chunk first; then prev/next |
| `item.candidate.score >= threshold` AND text is not short | Try prev AND next chunks |
| Adjacent chunk fetch returns `None` (chunk not found) | Keep original text unchanged; set `expanded=False`; log warning |
| Adjacent chunk fetch raises exception | Keep original text unchanged; log structured error with `chunk_id`; pipeline continues |
| Expansion succeeds | Prepend prev-chunk text + newline + original text + newline + next-chunk text; set `expanded=True` |
| Input is empty | Return `[]` |

## Expansion Priority

1. `parent_chunk_id` (if text < `expansion_min_chars`)
2. `previous_chunk_id` (prepend)
3. `next_chunk_id` (append)
All three may apply in a single expansion pass.

## Output

`list[CollectedItem]` — same length as input; items with successful expansion have
updated `text` content and `expanded=True`.

## Concrete Implementation

`src/core/evidence_orchestrator/expansion/lineage_expander.py`
→ `LineageExpander`

## Observability

Log: `stage="expand"`, `input_count`, `expanded_count`, `fetch_failures`,
`expansion_enabled`, `latency_ms`.
