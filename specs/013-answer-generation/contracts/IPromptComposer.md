# Contract: IPromptComposer

**Feature**: Answer Generation (spec 013)
**Module**: `core.answer_generation.interfaces`

## Purpose

`IPromptComposer` assembles the two-turn prompt (system message + user message) that
will be sent to the LLM. It is responsible for:

1. Embedding context blocks into the user message with citation markers (`[item_id]`).
2. Appending the user question.
3. Injecting the system instructions from `AnswerGenerationConfig.system_prompt_template`.
4. Appending capability modules (sorted by priority ascending).
5. **Not** injecting conflict-disclosure — that is `IPromptComposer`'s caller's
   responsibility (the pipeline injects disclosure into `ComposedPrompt.system_message`
   after composition).

## Interface

```python
class IPromptComposer(ABC):
    @abstractmethod
    def compose(
        self,
        context: Context,
        question: str,
        config: AnswerGenerationConfig,
    ) -> ComposedPrompt: ...
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `Context` | Fully-populated context (non-empty `ordered_blocks` guaranteed by caller) |
| `question` | `str` | The raw user question string |
| `config` | `AnswerGenerationConfig` | Provides `system_prompt_template` and `capability_modules` |

## Return: `ComposedPrompt`

| Field | Populated by this interface |
|-------|-----------------------------|
| `system_message` | System instructions + capability modules (without conflict disclosure) |
| `user_message` | Numbered context blocks (each prefixed `[item_id]`) + question |
| `has_conflict_disclosure` | Always `False` on return; set by pipeline after disclosure injection |
| `module_names` | Names of `capability_modules` included |

## Behaviour Contract

- `context.ordered_blocks` ordering MUST be preserved in the user message.
- Each block MUST be prefixed with `[{block.item_id}]` so the LLM can emit that token
  as a citation marker.
- `capability_modules` MUST be sorted by `priority` (ascending) before injection.
- If `capability_modules` is empty, no extra section is added.
- The composed prompt MUST NOT exceed any token limit enforced by the caller; the
  pipeline handles budget validation before calling the composer.
- The method is **synchronous** (no async needed; pure string assembly).

## Default Implementation

`DefaultPromptComposer` in `core.answer_generation.composition.default_composer`.

## Example Output (system_message fragment)

```
You are a precise question-answering assistant. Answer based strictly on
the provided context. Do not introduce information outside the context.
Cite sources by their block ID (e.g. [ei_4a7b3c9d]).
Return JSON: {"answer": "...", "confidence_note": "..."}.

## Domain: Pharmacy
Always include the BNF section reference when citing drug dosages.
```
