# Contract: Query Understanding Service

**Version**: 1.0.0 | **Feature**: `001-pharmacy-query-enhancement`

## Purpose

Internal application service contract for pharmacy-aware query classification and rewrite. Not exposed as a public HTTP endpoint in v1; consumed by `NLPController` before `search_vector_db_collection`.

## Interface

```python
class QueryUnderstandingService:
    async def analyze(
        self,
        *,
        query: str,
        chat_history: list[dict] | None = None,
        project: Project,
        language: str,
    ) -> QueryIntent: ...

    def build_retrieval_plan(
        self,
        intent: QueryIntent,
        *,
        base_limit: int,
        metadata_filter: dict | None = None,
    ) -> RetrievalPlan: ...
```

## Input

| Parameter | Type | Constraints |
|-----------|------|-------------|
| `query` | str | Non-empty, max 4000 chars |
| `chat_history` | list | Prior messages with `role` and `content.text` |
| `project` | Project | Must include `project_id` |
| `language` | str | `ar` or `en` |

## Output: QueryIntent

See [data-model.md](../data-model.md). JSON schema for LLM rewrite response:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["intent", "rewritten_queries", "retrieval_mode", "entities"],
  "properties": {
    "intent": {
      "enum": ["exhaustive_list", "drug_detail", "interaction_lookup", "prescription_check", "comparison", "general"]
    },
    "rewritten_queries": {
      "type": "array",
      "items": { "type": "string", "minLength": 2 },
      "minItems": 1,
      "maxItems": 8
    },
    "retrieval_mode": { "enum": ["standard", "exhaustive"] },
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["surface_form", "entity_type", "search_terms"],
        "properties": {
          "surface_form": { "type": "string" },
          "entity_type": { "enum": ["brand", "inn", "class", "form", "unknown"] },
          "search_terms": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "target_sources": {
      "type": "array",
      "items": { "type": "string" }
    },
    "prescription_drugs": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

## Error Handling

| Condition | Behavior |
|-----------|----------|
| LLM timeout (>3s) | Fall back to `PharmacyQueryClassifier` (rule-based) |
| Invalid JSON from LLM | Fall back to rule-based; log warning |
| Empty `rewritten_queries` | Use `[query]` |
| `PHARMACY_QUERY_REWRITE_ENABLED=false` | Skip LLM; rule-based only |

## Dependencies

- `generation_client` (LLMProviderFactory)
- `utils/pharmacy/classifier.py`
- `utils/pharmacy/prescription_parser.py`
- `helpers/config.py` → `PHARMACY_QUERY_REWRITE_ENABLED`, `PHARMACY_REWRITE_TIMEOUT_S`
