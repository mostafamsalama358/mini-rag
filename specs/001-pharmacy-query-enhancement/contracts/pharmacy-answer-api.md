# Contract: Pharmacy Answer API Extensions

**Version**: 1.0.0 | **Feature**: `001-pharmacy-query-enhancement`

## Endpoint (unchanged path)

`POST /api/v1/nlp/index/answer/{project_id}`

## Request — AnswerRequest (extended)

```json
{
  "text": "string (required)",
  "limit": 8,
  "session_id": "uuid | null",
  "metadata_filter": { "file_name": "NEWDRUGINTERACTION.xlsx" }
}
```

### Behavioral changes (backward compatible)

| Field | v1 behavior | v2 (this feature) behavior |
|-------|-------------|----------------------------|
| `limit` | Capped at request value | Minimum 50 when exhaustive intent detected |
| `text` | Used as-is for retrieval | Passed through query understanding + rewrite |
| `metadata_filter` | Applied to all retrieval passes | May be augmented with `target_sources` from intent |

No new required fields. Existing clients continue to work.

## Response — Success (extended)

```json
{
  "signal": "RAG_ANSWER_SUCCESS",
  "answer": "string — markdown with Summary/Details/Warnings/Source Coverage",
  "needs_clarification": false,
  "full_prompt": "string",
  "chat_history": [],
  "retrieval_meta": {
    "intent": "exhaustive_list",
    "retrieval_mode": "exhaustive",
    "documents_retrieved": 42,
    "queries_executed": ["كل الادوية المصنفة كباسط للعضلات", "muscle relaxant MYORELAXANT"],
    "entities": [
      { "surface_form": "باسط للعضلات", "entity_type": "class", "search_terms": ["muscle relaxant", "MYORELAXANT"] }
    ]
  },
  "citations": [
    {
      "doc_num": 1,
      "source_label": "FINALMEDICIN.xlsx",
      "file_name": "FINALMEDICIN.xlsx",
      "row_index": 15,
      "score": 0.87,
      "excerpt_preview": "ATRACURIUM BESYLATE, ..."
    }
  ]
}
```

### New optional fields

| Field | Type | Description |
|-------|------|-------------|
| `retrieval_meta` | object | Query understanding diagnostics (omit when rewrite disabled) |
| `citations` | array | Structured source citations per constitution §VI.4 |

**Note**: `citations` satisfies constitution requirement; human-readable Sources section remains in `answer` text.

## Response — Errors (unchanged)

| Status | signal | When |
|--------|--------|------|
| 400 | `RAG_NO_CONTEXT` | No indexed documents |
| 400 | `RAG_ANSWER_ERROR` | Generation failed |

## Search Endpoint Debug Contract

`POST /api/v1/nlp/index/search/{project_id}`

When `PHARMACY_QUERY_REWRITE_ENABLED=true`, search internally runs query understanding but response shape unchanged:

```json
{
  "signal": "VECTORDB_SEARCH_SUCCESS",
  "results": [
    {
      "text": "chunk text",
      "score": 0.92,
      "metadata": {
        "file_name": "FINALMEDICIN.xlsx",
        "row_index": 3,
        "chunking_strategy": "xlsx_row"
      }
    }
  ]
}
```

## Configuration Contract

| Env var | Default | Description |
|---------|---------|-------------|
| `PHARMACY_QUERY_REWRITE_ENABLED` | `true` | Enable LLM query rewrite |
| `PHARMACY_REWRITE_TIMEOUT_S` | `3` | Rewrite LLM timeout |
| `PHARMACY_ROW_CHUNKING` | `false` | Row-per-chunk XLSX ingestion |
| `PHARMACY_MAX_PAIR_QUERIES` | `15` | Max pairwise prescription queries |
| `PHARMACY_EXHAUSTIVE_MIN_LIMIT` | `50` | Floor for exhaustive retrieval |
| `PHARMACY_TARGET_SOURCES_JSON` | `{}` | Intent → file name hints map |

Example `PHARMACY_TARGET_SOURCES_JSON`:

```json
{
  "interaction_lookup": ["NEWDRUGINTERACTION.xlsx", "ALLMATERIAL1.xlsx"],
  "exhaustive_list": ["FINALMEDICIN.xlsx"],
  "drug_detail": ["FINALMEDICIN.xlsx", "ALLMATERIAL1.xlsx"]
}
```
