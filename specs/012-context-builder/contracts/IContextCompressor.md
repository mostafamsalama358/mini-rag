# Contract: `IContextCompressor`

**Module**: `src/core/context_builder/interfaces.py`
**Consumer**: `ContextBuilderPipeline` (stage 3 — Compression)

## Purpose

Reduces the token count of a single `EvidenceItem` text to fit within a target budget.
Returns the compressed text and its actual token count. Invoked only on items whose
`compressibility_score` exceeds the configured threshold.

## Interface

```python
class IContextCompressor(ABC):
    @abstractmethod
    async def compress(
        self,
        item: EvidenceItem,
        target_tokens: int,
        token_counter: ITokenCounter,
    ) -> tuple[str, int]:
        """
        Compress item.text to approximately target_tokens.

        Returns:
            (compressed_text, actual_token_count)

        Guarantees:
            - compressed_text is non-empty when item.text is non-empty.
            - actual_token_count ≤ target_tokens (best-effort; may exceed by
              at most one sentence if sentence-boundary splitting is used).
            - On internal error, raises ContextBuildError (pipeline catches and
              falls back to uncompressed inclusion or drop).
        """
```

## Contract Rules

1. `compressed_text` MUST be non-empty when `item.text` is non-empty.
2. `actual_token_count` SHOULD be `≤ target_tokens`. It MAY exceed by at most one
   sentence unit when sentence-boundary splitting is used; the pipeline accounts for
   this tolerance.
3. The implementation MUST NOT modify `item` in place; it returns a new `(str, int)`.
4. MUST raise `ContextBuildError` (not a raw exception) on unrecoverable failure; the
   pipeline catches this and falls back to full inclusion or drop.
5. `target_tokens` of `0` → return `("", 0)` (no text fits; pipeline will drop item).

## Implementations

### `HeuristicTruncationCompressor` (default)
`src/core/context_builder/compression/heuristic_compressor.py`

Algorithm: split `item.text` on sentence boundaries (`(?<=[.?!])\s+`); greedily
append sentences until the next sentence would exceed `target_tokens`; return the
accumulated text. Falls back to a hard character truncation if no sentence boundary
is found within the first `target_tokens * 4` characters (4 chars ≈ 1 token).

No LLM call. Synchronous computation inside an `async def` (no blocking I/O).

### `LLMContextCompressor` (optional)
`src/core/context_builder/compression/llm_compressor.py`

Algorithm: calls `LLMProviderFactory` to summarize `item.text` to approximately
`target_tokens` words. Activated via `compression_strategy: "llm"` in config.

## Selection

`ContextBuilderRegistry` selects the implementation based on
`ContextBuilderConfig.compression_strategy`:

```
"heuristic" → HeuristicTruncationCompressor  (default)
"llm"       → LLMContextCompressor
```
