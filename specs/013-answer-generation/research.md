# Research: Answer Generation (spec 013)

**Date**: 2026-07-14 | **Phase**: 0 (pre-design)

---

## R-01: Context.schema_version — Cross-Spec Dependency Resolved

**Question**: Does spec 012's `Context` model already expose a `schema_version` field,
making FR-010 implementable as-is?

**Finding**: Yes. The live implementation at
`src/core/context_builder/models.py` already defines:

```python
SCHEMA_VERSION = "1.0.0"

class Context(BaseModel):
    ...
    schema_version: str = SCHEMA_VERSION
    ...
```

The field is part of the frozen `Context` Pydantic model. The cross-spec dependency
note in the spec Assumptions section (`[Cross-spec dependency — resolve before /plan]`)
was raised against the *spec 012 document*, which did not list `schema_version` under
Key Entities. The **code contract is already correct**.

**Decision**: FR-010 is implementable immediately using the established pattern from
`context_builder/pipeline.py`:

```python
def _validate_context_version(context: Context, config: AnswerGenerationConfig) -> None:
    expected_major = config.context_schema_version.split(".", maxsplit=1)[0]
    actual_major = context.schema_version.split(".", maxsplit=1)[0]
    if expected_major != actual_major:
        raise SchemaVersionError(
            f"Context schema major version {actual_major!r} "
            f"does not match expected {expected_major!r}"
        )
```

**Action**: Update the spec 013 Assumptions to reflect that this dependency is
resolved. No spec 012 change is required.

---

## R-02: Citation Map Key Contract

**Question**: Are `Context.citation_map` keys confirmed to be `item_id` values, giving
`ICitationFormatter` an unambiguous lookup key?

**Finding**: Confirmed. The `Context` model enforces this via a `@model_validator`:

```python
@model_validator(mode="after")
def _citation_completeness(self) -> Context:
    block_ids = {block.item_id for block in self.ordered_blocks}
    citation_ids = set(self.citation_map.keys())
    if block_ids != citation_ids:
        raise ValueError(
            "ordered_blocks item_ids must match citation_map keys exactly"
        )
    return self
```

`citation_map: dict[str, Citation]` — keys are `ContextBlock.item_id` strings
(prefixed `ei_`, e.g. `ei_4a7b3c9d1e2f5678`).

The `Citation` type (from `core.evidence_orchestrator.models`) carries:
`document_id`, `chunk_id`, `retrieval_score`, `score_source`, `page_number`,
`section_title`, `document_title`, `chunk_index`.

**Decision**: `ICitationFormatter` resolves LLM-emitted `item_id` markers by direct
dict lookup against `Context.citation_map`. No alias or secondary key needed.
Citation markers in the prompt will be the raw `item_id` strings (e.g.
`[ei_4a7b3c9d]`); `IPromptComposer` is responsible for embedding them in the
context blocks during prompt assembly.

---

## R-03: LLM Call Surface

**Question**: Which `LLMInterface` method does the pipeline call, and how does it
interact with async?

**Finding**: `LLMInterface` (at `src/stores/llm/LLMInterface.py`) defines:

```python
async def generate_text_async(
    self,
    prompt: str,
    chat_history: list = None,
    max_output_tokens: int = None,
    temperature: float = None,
    *,
    response_mime_type: str = None,
    response_schema: dict = None,
) -> ...:
    # Default: delegates to asyncio.to_thread(self.generate_text, ...)
```

All providers expose `generate_text_async`. Providers with a native async client
(e.g. `AsyncOpenAI`) override the default; others run in a thread pool automatically.
No blocking call in the event loop.

**Decision**: `AnswerGenerationPipeline` calls `llm.generate_text_async(...)`. The
pipeline does **not** call `generate_text` directly. `response_mime_type="application/json"`
and an optional `response_schema` dict are passed when the provider supports
structured/JSON-mode output (configurable in `AnswerGenerationConfig`).

**Rationale**: Consistent with async-first constitution mandate; thread-pool fallback
means sync-only providers (Cohere, BGE) still work without pipeline changes.

---

## R-04: LLM Output Parsing Strategy

**Question**: Should the output contract be enforced via JSON-mode structured generation
or post-parse validation of plain text?

**Options considered**:

| Option | Pros | Cons |
|--------|------|------|
| A. JSON-mode only | Clean schema enforcement, no regex | Only works with OpenAI / Gemini; Cohere/BGE lack JSON-mode |
| B. Plain-text + regex | Provider-agnostic | Brittle, hard to version |
| C. Attempt JSON-mode; fallback to plain-text Pydantic parse | Provider-agnostic, schema-enforced when possible | Slightly more complexity in `IOutputParser` |

**Decision**: Option C — `JsonOutputParser` attempts JSON-mode parse first; on
`json.JSONDecodeError` it falls back to a structured plain-text extraction heuristic.
The `AnswerResult` Pydantic model validates the final parsed output regardless of path.
This matches the pattern used in spec 010 (retrieval engine) for provider-agnostic
output handling.

---

## R-05: Conflict Disclosure Injection Approach

**Question**: How should conflict disclosure be injected — as a separate system-prompt
section, or as inline annotations in the assembled context blocks?

**Finding**: `Context.conflicts` is a `list[ConflictGroup]`, where each group carries:
- `entity_tag: str` — the entity name
- `attribute: str` — the conflicting attribute
- `item_ids: list[str]` — the contributing block IDs (≥ 2)
- `resolution: str | None` — e.g. `"budget_drop"` or `None`

**Decision**: Inject as a **dedicated section in the system prompt**, not inline.
`IPromptComposer` appends a `## Conflicting Information` section listing each
conflict group when `Context.conflicts` is non-empty. This keeps context blocks clean
(no modification of retrieved text), is easily testable in isolation, and produces a
predictable output that the grounding check can inspect for disclosure language.

---

## R-06: Grounding Check Implementation Strategy

**Question**: How does the lightweight `IGroundingChecker` detect ungrounded claims
without a second LLM call?

**Finding**: `Context.citation_map` values are `Citation` objects (not `EvidenceItem`s),
so `EvidenceItem.entity_tags` are **not** present anywhere in the `Context` object.
The grounding checker must operate exclusively on what `Context` exposes directly.
`Context.ordered_blocks` contains `ContextBlock` instances, each with a `text` field
— the raw block text is the only ground-truth vocabulary available at this stage
without going back to the upstream `EvidencePack`.

**Decision**: Build a `context_vocabulary` from `ContextBlock.text` values, not from
`entity_tags`.

1. Build `context_vocabulary`: the union of all lowercase words found in
   `ContextBlock.text` across `context.ordered_blocks`.
2. Scan `answer_text` for candidate entities: title-cased sequences of two or more
   consecutive words that are absent from `context_vocabulary` (simple heuristic, no
   NER model required).
3. Emit a `GroundingFlag(entity=entity, claim=<surrounding sentence>,
   reason="entity_not_in_context")` for each candidate not in `context_vocabulary`.

This is the **lightweight** implementation matching `IGroundingChecker`'s flag-only
contract. Deep semantic faithfulness scoring (spec 014) replaces this at evaluation
time.

**Rationale**: Zero LLM calls, sub-millisecond for typical answer lengths; no external
dependencies; no upstream `EvidencePack` access required; easy to replace with a
smarter implementation later.

---

## R-07: Field-Pack Config Structure

**Question**: What keys should `answer_generation.yaml` expose, following the pattern
of `context_builder.yaml`?

**Decision**: Minimal, domain-agnostic config keys:

```yaml
# src/fields/generic/answer_generation.yaml
context_schema_version: "1.0.0"    # expected Context major version (FR-010)
max_output_tokens: 2048
temperature: 0.3
grounding_check_enabled: true
no_answer_message: "The answer could not be found in the provided sources."
conflict_disclosure_header: "## Conflicting Information"
system_prompt_template: |           # versioned; domain packs override
  You are a precise question-answering assistant. Answer based strictly on
  the provided context. Do not introduce information outside the context.
  Return your answer as JSON: {"answer": "...", "confidence_note": "..."}.
capability_modules: []              # domain packs inject entries here
schema_version: "1.0.0"
```

Domain packs (`pharmacy/answer_generation.yaml`, `legal/answer_generation.yaml`)
override `system_prompt_template` and append `capability_modules` entries.

---

## R-08: No-Answer Short-Circuit

**Question**: At which stage should the empty-context guard fire, and what does it
return?

**Decision**: First check after schema version validation (before prompt composition).
If `len(context.ordered_blocks) == 0`, the pipeline returns immediately:

```python
AnswerResult(
    answer=config.no_answer_message,
    citations=[],
    confidence_note=None,
    conflicts_disclosed=False,
    no_answer=True,
    grounding_flags=[],
    plan_id=context.plan_id,
    context_id=context.context_id,
)
```

No LLM call is made. The log entry records `no_answer=True` and `elapsed_ms`.
Consistent with `context_builder` pattern of returning an `_empty_context` sentinel.

---

## R-09: Context.plan_id and Context.context_id — Fields Confirmed Present

**Question**: Does the live `Context` model expose `plan_id` and `context_id` fields,
so `AnswerResult` can thread them through without additional pipeline parameters?

**Finding**: Confirmed. `src/core/context_builder/models.py` defines:

```python
class Context(BaseModel):
    context_id: str
    pack_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION
    ...
```

Both `context_id` (prefixed `ctx_`, e.g. `ctx_4a7b3c9d1e2f5678`) and `plan_id`
(prefixed `plan_`) are first-class fields on the frozen `Context` model. They are
populated by the Context Builder pipeline before the `Context` is handed off to Answer
Generation.

**Decision**: `AnswerGenerationPipeline.run()` reads `context.context_id` and
`context.plan_id` directly and copies them into `AnswerResult`. No additional
pipeline parameters are needed, and no changes to spec 012 are required.

**Action**: Spec 013 Assumptions updated to record this as confirmed (see below).

---

## Resolution Summary

| ID | Decision |
|----|----------|
| R-01 | `Context.schema_version` already present; FR-010 implementable now |
| R-02 | `citation_map` keys = `item_id`; `ICitationFormatter` uses direct dict lookup |
| R-03 | Pipeline calls `llm.generate_text_async()`; thread-pool fallback handles sync providers |
| R-04 | JSON-mode parse with plain-text fallback in `JsonOutputParser` |
| R-05 | Conflict disclosure injected as system-prompt section, not inline in blocks |
| R-06 | Grounding check = vocabulary from `ContextBlock.text`; zero LLM calls; no `EvidencePack` access needed |
| R-07 | 9 config keys in `answer_generation.yaml`; domain packs override prompt + modules |
| R-08 | No-answer guard fires after version check, before prompt composition; returns sentinel `AnswerResult` |
| R-09 | `Context.plan_id` and `Context.context_id` confirmed present; threaded into `AnswerResult` directly |
