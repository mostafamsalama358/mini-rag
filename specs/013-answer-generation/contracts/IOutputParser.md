# Contract: IOutputParser

**Feature**: Answer Generation (spec 013)
**Module**: `core.answer_generation.interfaces`

## Purpose

`IOutputParser` transforms the raw string (or JSON object) returned by the LLM into a
partial `AnswerResult`. "Partial" means citations are not yet resolved — the raw answer
text still contains `item_id` markers (e.g. `[ei_4a7b3c9d]`). Citation resolution is
the responsibility of `ICitationFormatter` in the next stage.

## Interface

```python
class IOutputParser(ABC):
    @abstractmethod
    def parse(
        self,
        raw: str,
        config: AnswerGenerationConfig,
    ) -> tuple[str, str | None]: ...
```

Return value: `(answer_text, confidence_note)` — both strings, both potentially empty.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `raw` | `str` | Raw LLM response (JSON string or plain text) |
| `config` | `AnswerGenerationConfig` | Access to schema expectations |

## Behaviour Contract

- MUST attempt JSON parse first (`json.loads(raw)`).
  - On success: extract `raw["answer"]` and `raw.get("confidence_note")`.
  - On `JSONDecodeError` or missing `"answer"` key: fall back to treating the entire
    `raw` string as the answer text, with `confidence_note=None`.
- The returned `answer_text` MUST be a non-empty string. If the LLM returns an empty
  string or `null`, the parser MUST substitute the `config.no_answer_message` and
  signal the pipeline to set `no_answer=True` — this is communicated by returning an
  empty `answer_text` (empty string signals no-answer to the caller).
- The parser MUST NOT resolve citation markers — `item_id` tokens in the text are
  preserved as-is for `ICitationFormatter`.
- The method is **synchronous** (pure string transformation).

## Error Handling

- A completely unparseable response (not JSON, not plain text) MUST raise
  `AnswerGenerationError` with a descriptive message including the raw response length
  and first 100 characters.

## Default Implementation

`JsonOutputParser` in `core.answer_generation.parsing.json_output_parser`.

## Parse Strategy (Decision R-04)

```
raw LLM string
    │
    ├─ json.loads() succeeds?
    │   ├─ Yes → extract "answer", "confidence_note"
    │   └─ No  → treat entire string as answer_text, confidence_note=None
    │
    └─ answer_text empty / null?
        ├─ Yes → return ("", None)  ← pipeline interprets as no_answer
        └─ No  → return (answer_text, confidence_note)
```
