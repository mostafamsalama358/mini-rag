# Data Model: Answer Generation (spec 013)

**Date**: 2026-07-14 | **Schema version**: `1.0.0`

All models are **frozen Pydantic `BaseModel`** instances following the codebase
convention (`model_config = ConfigDict(frozen=True)`). Mutable lists / dicts are
wrapped in `Field(default_factory=...)`.

---

## Input Contract (consumed, not owned)

### `Context` _(from `core.context_builder.models`, spec 012)_

Consumed read-only. Key fields used by this pipeline:

| Field | Type | Used by stage |
|-------|------|---------------|
| `context_id` | `str` | carried into `AnswerResult` |
| `plan_id` | `str` | logging, carried into `AnswerResult` |
| `schema_version` | `str` | FR-010 version gate |
| `ordered_blocks` | `list[ContextBlock]` | empty-context guard; prompt composition |
| `citation_map` | `dict[str, Citation]` | citation formatting (`item_id` → `Citation`) |
| `conflicts` | `list[ConflictGroup]` | conflict-disclosure injection |
| `token_count` | `int` | logging |

### `ContextBlock` _(from `core.context_builder.models`, spec 012)_

| Field | Type | Notes |
|-------|------|-------|
| `item_id` | `str` | citation marker embedded in prompt (e.g. `[ei_4a7b…]`) |
| `document_id` | `str` | informational |
| `section_path` | `str \| None` | included in prompt header for each block |
| `text` | `str` | block content included in prompt; scanned by grounding checker |
| `token_count` | `int` | for logging |
| `compressed` | `bool` | informational |

### `Citation` _(from `core.evidence_orchestrator.models`, spec 011)_

| Field | Type | Mapped to `CitationReference` |
|-------|------|-------------------------------|
| `document_id` | `str` | → `CitationReference.document_id` |
| `chunk_id` | `str` | → `CitationReference.chunk_id` |
| `retrieval_score` | `float` | → `CitationReference.retrieval_score` |
| `section_title` | `str \| None` | → `CitationReference.section_title` |
| `document_title` | `str \| None` | → `CitationReference.document_title` |
| `page_number` | `int \| None` | → `CitationReference.page_number` |

### `ConflictGroup` _(from `core.context_builder.models`, spec 012)_

| Field | Type | Used by stage |
|-------|------|---------------|
| `entity_tag` | `str` | conflict-disclosure injection |
| `attribute` | `str` | conflict-disclosure injection |
| `item_ids` | `list[str]` | cross-reference with prompt block ids |
| `resolution` | `str \| None` | informational note in disclosure |

---

## Output Models (owned by this feature)

### `AnswerResult`

The stable public output contract consumed by spec 013 (Answer Generation API) and
logged for spec 014 (Answer Quality).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `answer` | `str` | yes | Final answer text (or no-answer message) |
| `citations` | `list[CitationReference]` | yes | Resolved citations; empty on no-answer |
| `confidence_note` | `str \| None` | no | LLM-generated confidence / limitation note |
| `conflicts_disclosed` | `bool` | yes | True iff conflict-disclosure was injected and answer contains disclosure |
| `no_answer` | `bool` | yes | True iff context was empty and LLM was not called |
| `grounding_flags` | `list[GroundingFlag]` | yes | Ungrounded claim flags; empty if check passes |
| `plan_id` | `str` | yes | Threaded from `Context.plan_id` for correlation |
| `context_id` | `str` | yes | Threaded from `Context.context_id` for traceability |
| `schema_version` | `str` | yes | Always `"1.0.0"` |

**Validation rules**:
- `answer` must be non-empty (even for no-answer, the no-answer message is non-empty)
- `citations` must be empty when `no_answer=True`
- `schema_version` must match `"1.0.0"` major

---

### `CitationReference`

Resolved citation entry in `AnswerResult.citations`. One entry per `item_id` marker
the LLM emitted that resolves in `Context.citation_map`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `citation_id` | `str` | yes | The `item_id` key used for lookup (e.g. `ei_4a7b3c9d`) |
| `document_id` | `str` | yes | From `Citation.document_id` |
| `chunk_id` | `str` | yes | From `Citation.chunk_id` |
| `document_title` | `str \| None` | no | From `Citation.document_title` |
| `section_title` | `str \| None` | no | From `Citation.section_title` |
| `page_number` | `int \| None` | no | From `Citation.page_number` |
| `retrieval_score` | `float` | yes | From `Citation.retrieval_score` |

**Ordering**: citations are ordered by their first appearance in the answer text (left-
to-right scan of `item_id` markers). Duplicate markers in the text yield a single entry.

---

### `GroundingFlag`

One flag per suspected ungrounded entity or claim detected by `IGroundingChecker`.
Non-blocking — presence of flags does not prevent `AnswerResult` from being returned.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity` | `str` | yes | The entity string that was not found in context |
| `claim` | `str` | yes | The text span or sentence containing the entity |
| `reason` | `str` | yes | Short reason code, e.g. `"entity_not_in_context"` |

---

## Internal Models

### `ComposedPrompt`

Internal-only output of `IPromptComposer`; not exposed beyond the pipeline.

| Field | Type | Description |
|-------|------|-------------|
| `system_message` | `str` | System prompt (instructions + conflict disclosure + domain modules) |
| `user_message` | `str` | User-facing turn (context blocks + question) |
| `has_conflict_disclosure` | `bool` | True iff conflict-disclosure section was injected |
| `module_names` | `list[str]` | Names of capability modules included (for logging) |

---

### `CapabilityModule`

Config-injected domain instruction block. Comes from `answer_generation.yaml` field-
pack; never hardcoded in core.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Module identifier (e.g. `"pharmacy_dosage_instructions"`) |
| `instructions` | `str` | Raw instruction text appended to system prompt |
| `priority` | `int` | Lower = higher priority (injected first); default `0` |

---

## Configuration Model

### `AnswerGenerationConfig`

Loaded from `src/fields/{domain}/answer_generation.yaml`; resolved generic < domain <
project.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `context_schema_version` | `str` | `"1.0.0"` | Expected `Context.schema_version` major for FR-010 gate |
| `max_output_tokens` | `int` | `2048` | Passed to `LLMInterface.generate_text_async` |
| `temperature` | `float` | `0.3` | Passed to `LLMInterface.generate_text_async` |
| `grounding_check_enabled` | `bool` | `True` | Toggle `IGroundingChecker` |
| `no_answer_message` | `str` | `"The answer could not be found in the provided sources."` | Returned when `no_answer=True` |
| `conflict_disclosure_header` | `str` | `"## Conflicting Information"` | Section header injected before conflict list |
| `system_prompt_template` | `str` | see below | Base system instructions; domain packs override |
| `capability_modules` | `list[CapabilityModule]` | `[]` | Domain-specific instruction modules |
| `schema_version` | `str` | `"1.0.0"` | Config schema version |

---

## Field-Pack Config File Structure

```yaml
# src/fields/generic/answer_generation.yaml
context_schema_version: "1.0.0"
max_output_tokens: 2048
temperature: 0.3
grounding_check_enabled: true
no_answer_message: "The answer could not be found in the provided sources."
conflict_disclosure_header: "## Conflicting Information"
system_prompt_template: |
  You are a precise question-answering assistant. Answer based strictly on
  the provided context. Do not introduce information outside the context.
  Cite sources by their block ID (e.g. [ei_4a7b3c9d]).
  Return JSON: {"answer": "...", "confidence_note": "..."}.
capability_modules: []
schema_version: "1.0.0"
```

Domain packs override `system_prompt_template` and append `capability_modules`.

---

## Stage-to-Model Mapping

| Stage | Input | Output |
|-------|-------|--------|
| 1. Version gate | `Context.schema_version`, `AnswerGenerationConfig.context_schema_version` | raises `SchemaVersionError` or continues |
| 2. No-answer guard | `Context.ordered_blocks` | `AnswerResult(no_answer=True)` or continues |
| 3. Prompt Composition | `Context`, `question: str`, `AnswerGenerationConfig` | `ComposedPrompt` |
| 4. Conflict Disclosure Injection | `Context.conflicts`, `ComposedPrompt` | mutated `ComposedPrompt` (has_conflict_disclosure=True) |
| 5. LLM Call | `ComposedPrompt`, `LLMInterface` | raw `str` response |
| 6. Output Parsing | raw `str`, `Context.citation_map` | partial `AnswerResult` |
| 7. Citation Formatting | partial `AnswerResult`, `Context.citation_map` | `AnswerResult` with resolved `citations` |
| 8. Grounding Check | `AnswerResult.answer`, `Context.ordered_blocks` | `list[GroundingFlag]` appended to `AnswerResult` |
