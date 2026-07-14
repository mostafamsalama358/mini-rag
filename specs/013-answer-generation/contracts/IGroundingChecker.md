# Contract: IGroundingChecker

**Feature**: Answer Generation (spec 013)
**Module**: `core.answer_generation.interfaces`

## Purpose

`IGroundingChecker` inspects the generated answer text for claims or entities that
cannot be traced back to the provided `Context`. It emits `GroundingFlag` entries for
each suspected ungrounded element. It **never blocks or retries** — the pipeline always
returns the answer regardless of flag count.

Deep faithfulness scoring (semantic NLI, cross-encoder entailment) is explicitly out of
scope; that belongs to spec 014 (Answer Quality). This interface is the lightweight,
latency-free, flag-only gate.

## Interface

```python
class IGroundingChecker(ABC):
    @abstractmethod
    def check(
        self,
        answer_text: str,
        context: Context,
    ) -> list[GroundingFlag]: ...
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `answer_text` | `str` | The final answer text (post-parsing, pre-return) |
| `context` | `Context` | Read-only; `ordered_blocks` provides the ground truth text |

## Behaviour Contract

- MUST return an empty list when no ungrounded entities are detected.
- MUST return an empty list when `AnswerGenerationConfig.grounding_check_enabled` is
  `False` — the pipeline skips calling this interface entirely in that case.
- MUST NOT make any LLM calls, network calls, or blocking I/O.
- MUST NOT modify `answer_text` or `context`.
- MUST NOT raise exceptions for individual flag failures — log and continue.
- The method is **synchronous** (in-memory text comparison only).
- Total runtime MUST be sub-millisecond for typical answer lengths (< 1 000 tokens)
  on standard hardware (SC-006).

## Default Implementation Strategy (R-06)

`EntityTagGroundingChecker` in `core.answer_generation.grounding.entity_tag_checker`.

`Context.citation_map` values are `Citation` objects — `EvidenceItem.entity_tags` are
not present in `Context`. The checker operates exclusively on `Context.ordered_blocks`,
which carries `ContextBlock.text` — the only ground-truth vocabulary available without
going back to the upstream `EvidencePack`.

Steps:

1. Build `context_vocabulary`: the union of all lowercase words from all
   `ContextBlock.text` values in `context.ordered_blocks`.
2. Scan `answer_text` for candidate entities: title-cased sequences of two or more
   consecutive words absent from `context_vocabulary` (simple heuristic; no NER model).
3. For each candidate entity not in `context_vocabulary`:
   - Emit `GroundingFlag(entity=entity, claim=<surrounding sentence>, reason="entity_not_in_context")`.

## Error Handling

- Any internal error in the checker MUST be caught, logged at `WARNING` level with the
  exception message, and the method MUST return an empty list (fail-open).

## Extensibility

Future implementations may use:
- BM25 term overlap between answer and context blocks (higher recall)
- Cross-encoder entailment score (spec 014 territory)
- Named-entity recognition with an in-process NER model

Any such implementation MUST satisfy the same interface and the sub-millisecond
constraint (or document the latency trade-off and update SC-006).

## Example

```python
flags = checker.check(
    answer_text="The patient should take Metformin XR and monitor blood glucose [ei_4a7b].",
    context=context,  # context blocks contain "Metformin" but not "Metformin XR"
)
# → [GroundingFlag(entity="Metformin XR", claim="The patient should take Metformin XR...", reason="entity_not_in_context")]
```
