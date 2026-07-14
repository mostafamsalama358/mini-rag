# Contract: `ITokenBudgetAllocator`

**Module**: `src/core/context_builder/interfaces.py`
**Consumer**: `ContextBuilderPipeline` (stage 1 — Token Budget Allocation)

## Purpose

Computes the number of tokens available for evidence content, given the total model
context window and the space reserved for system prompt, user question, and model output.
Returns a single integer: the usable evidence budget.

## Interface

```python
class ITokenBudgetAllocator(ABC):
    @abstractmethod
    def allocate(self, config: ContextBuilderConfig) -> int:
        """
        Returns the number of tokens available for evidence content.

        Must return a non-negative integer. Returns 0 when reservations
        exceed or equal total_context_window (never raises).
        """
```

## Contract Rules

1. Return value MUST be `≥ 0`. Negative values are a contract violation.
2. When `reservations.system_prompt + reservations.question + reservations.output
   ≥ config.total_context_window`, return `0` (not an error — caller handles
   empty-budget gracefully).
3. MUST be synchronous (no `async`). Budget allocation is a pure arithmetic operation.
4. MUST NOT have side effects (no logging, no I/O, no state mutation).

## Default Implementation

`DefaultTokenBudgetAllocator` in `src/core/context_builder/budget/default_allocator.py`:

```python
def allocate(self, config: ContextBuilderConfig) -> int:
    reserved = (
        config.reservations.system_prompt
        + config.reservations.question
        + config.reservations.output
    )
    return max(0, config.total_context_window - reserved)
```

Equivalent to `config.available_budget` computed property — the implementation exists
so callers always go through the interface and can swap for a model-aware allocator
(e.g., one that queries a live model API for its actual context window size).

## Extension Points

A model-aware implementation may:
- Accept the model name and look up the actual context window from a provider registry.
- Adjust reservations dynamically based on prompt template length.

The interface signature does not expose these concerns; they are resolved by the
concrete implementation during construction.
