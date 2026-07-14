# Contract: `IEvidenceCollector`

**Module**: `src/core/evidence_orchestrator/interfaces.py`
**Stage**: Collect (stage 1 of 6)

## Purpose

Transforms a `RetrievalResult` from spec 010 into a flat list of `CollectedItem`
objects, tagging each with its originating strategy and computing an initial token
estimate. This is the Orchestrator's entry point; all downstream stages operate on
`CollectedItem` or `EvidenceItem` exclusively.

## Protocol Definition

```python
class IEvidenceCollector(ABC):
    @abstractmethod
    async def collect(
        self,
        result: RetrievalResult,
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]: ...
```

## Behaviour Contract

| Condition | Expected Behaviour |
|-----------|-------------------|
| `result.candidates` is empty | Return `[]` immediately; no error raised |
| `result.candidates` has N items | Return exactly N `CollectedItem` objects, one per candidate |
| `candidate.source_ref` is `None` | `CollectedItem` constructed with `strategy_id` from `RetrievalTrace` steps matching the candidate; raw_token_count estimated from `content_excerpt` length |
| `token_counter` is `"tiktoken"` but tiktoken unavailable | Fall back to character approximation; log structured warning |

## Output

`list[CollectedItem]` — ordering preserves the rank order from `RetrievalResult.candidates`.

## Concrete Implementation

`src/core/evidence_orchestrator/collection/retrieval_result_collector.py`
→ `RetrievalResultCollector`

## Observability

Log at method entry/exit: `stage="collect"`, `input_count`, `output_count`, `latency_ms`.
