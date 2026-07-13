# Contract: Query Understanding (Semantic Parser)

**Version**: 1.0.0 | **Feature**: `004-semantic-query-parser` | **Date**: 2026-07-06

## Overview

Query Understanding is an **internal application boundary** between the chat/answer orchestration layer and retrieval. External HTTP APIs are unchanged; this contract defines the module interface and the structured artifact consumed by retrieval.

```text
answer_service.answer_question()
    → semantic_parse_async(...) → ParseResult
    → retrieval.search(..., query_plan=ParseResult.query_plan, text=ParseResult.canonical_query)
```

---

## Internal API: `semantic_parse_async`

**Module**: `core.query_parser`

```python
async def semantic_parse_async(
    query: str,
    *,
    generation_client,
    profile: FieldProfile,
    conversation_context: ConversationContext,
    catalog_terms: list[str] | None = None,
    catalog_fingerprint_index: dict[str, str] | None = None,
) -> ParseResult:
    """Parse user question into canonical query + QueryPlan.

    Raises no exceptions for parse failures — returns degraded ParseResult
    with needs_clarification or field=unknown per FR-014.
    """
```

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | yes | Raw user question (pre-normalized by caller optional) |
| `generation_client` | `LLMInterface` | yes | Injected generation provider |
| `profile` | `FieldProfile` | yes | Merged field pack; supplies `parser_profile`, `field_registry` |
| `conversation_context` | `ConversationContext` | yes | Bounded session context |
| `catalog_terms` | `list[str]` | no | Project entity lexicon for grounding |
| `catalog_fingerprint_index` | `dict` | no | Pre-built fingerprint index |

### Output: `ParseResult`

| Field | Type | Always present |
|-------|------|----------------|
| `original_query` | `str` | yes |
| `canonical_query` | `str` | yes |
| `query_plan` | `QueryPlan` | yes |
| `used_llm` | `bool` | yes |
| `latency_ms` | `float` | yes |
| `grounding_score` | `float \| null` | yes |
| `error` | `str \| null` | yes |

---

## `QueryPlan` JSON Schema (v1)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://algorag.local/schemas/query-plan/v1",
  "type": "object",
  "required": ["entity", "field", "operation", "scope", "language", "needs_clarification"],
  "properties": {
    "entity": { "type": ["string", "null"] },
    "entities": { "type": "array", "items": { "type": "string" } },
    "field": { "type": "string" },
    "operation": {
      "type": "string",
      "enum": ["lookup", "list", "compare", "explain", "count", "unsupported"]
    },
    "scope": {
      "type": "string",
      "enum": ["all", "single", "subset"]
    },
    "language": { "type": "string", "pattern": "^[a-z]{2}$" },
    "filters": { "type": "object" },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "needs_clarification": { "type": "boolean" },
    "clarification_prompt": { "type": "string" }
  },
  "additionalProperties": false
}
```

---

## Retrieval consumer contract

**Module**: `services/rag/answer_service` → `nlp_controller.search_vector_db_collection`

### New parameters

```python
async def search_vector_db_collection(
    ...,
    text: str,                          # canonical_query
    query_plan: QueryPlan | None = None,  # structured intent
    field_resolution: FieldResolution | None = None,  # derived from plan
) -> list[RetrievedDocument]:
```

### Rules (FR-004)

| Source | Used for |
|--------|----------|
| `query_plan.entity` | `metadata_filter` on entity column |
| `query_plan.field` → `field_resolution` | Column targeting / boost |
| `query_plan.operation` + `scope` | Retrieval limit, exhaustive mode |
| `canonical_query` (`text`) | Dense + sparse search strings only |
| `query_plan.needs_clarification` | **Must not** call retrieval |

### Prohibited

- Deriving structured filters from `canonical_query` text
- Parallel intent classification when `query_plan` is present
- `query_variants` from legacy rewrite pipeline when semantic parser enabled

---

## Field pack contract: `parser.yaml`

**Path**: `src/fields/{domain}/parser.yaml`

**Required keys**:

| Key | Type | Description |
|-----|------|-------------|
| `prompt` | `string` | Parser instructions (must reference registry fields) |
| `document_language` | `string` | Canonical output language |

**Optional keys**: `timeout_seconds`, `max_output_tokens`, `temperature`, `context_turn_window`, `entity_grounding`, `allowed_fields`

**Loader**: `FieldRegistry._load_parser` → `FieldProfile.parser_profile`

**Deprecation**: `query_rewrite.yaml` MUST NOT be read when `RAG_SEMANTIC_PARSER_ENABLED=true`.

---

## `build_conversation_context`

**Module**: `core.query_parser.context`

```python
def build_conversation_context(
    *,
    domain_key: str,
    document_language: str,
    chat_messages: list[ChatMessage],
    context_turn_window: int = 4,
) -> ConversationContext:
```

Extracts `current_entity` from most recent message metadata containing grounded `query_plan.entity`.

---

## `resolve_from_plan`

**Module**: `core.field_resolution`

```python
def resolve_from_plan(
    plan: QueryPlan,
    registry: FieldRegistryProfile,
    manifest: FieldManifest | None = None,
) -> FieldResolution | None:
```

Maps `plan.field` → concept profile → column keys. Returns `None` when `field == "unknown"`.

---

## Observability contract

### Log event: `query_parse_complete`

| Field | Type |
|-------|------|
| `request_id` | string |
| `project_id` | string |
| `domain_key` | string |
| `canonical_query` | string |
| `query_plan` | object |
| `grounding_score` | float \| null |
| `parse_latency_ms` | float |
| `needs_clarification` | bool |

### Metric: `RAG_PARSE_LATENCY`

- Type: histogram
- Labels: `project_id`, `domain_key`, `outcome` ∈ `ok`, `clarify`, `fallback`
- Buckets: 100ms – 5s

---

## HTTP API impact

**No breaking changes** to `/api/v1/nlp/*` request/response shapes in v1.

Optional debug field (future): `?debug_parse=true` returns `query_plan` in response metadata — out of scope v1.

---

## Feature flag

| Env var | Default (P4+) | Description |
|---------|---------------|-------------|
| `RAG_SEMANTIC_PARSER_ENABLED` | `true` | Enable semantic parser path |
| `RAG_SEMANTIC_PARSER_SHADOW` | `false` | Log new plan while running legacy (P3 only) |

---

## Golden-set contract

**Path**: `tests/golden/query_parser/pharmacy_golden.yaml`

```yaml
cases:
  - id: euthyrox_strengths_ar
    query: "ايه كل تركيزات يوثيروكس؟"
    context: {}
    expect:
      entity: EUTHYROX
      field: strengths
      operation: list
      scope: all
  - id: euthyrox_interactions_followup
    query: "ايه الادوية المتعارضة معاه؟"
    context:
      current_entity: EUTHYROX
    expect:
      entity: EUTHYROX
      field: interactions
      operation: list
      scope: all
```

**Runner**: `scripts/run_query_parser_golden.py` — exits non-zero if below SC-002 thresholds.
