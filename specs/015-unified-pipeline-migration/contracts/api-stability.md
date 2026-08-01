# Contract: API Stability

**Feature**: 015-unified-pipeline-migration | **Version**: 1.0.0

Normative contract for backward compatibility. **No client changes permitted or required.**

---

## Endpoint

```text
POST /api/v1/nlp/{project_id}/answer
```

Route handler: `routes/nlp.py::answer_rag`

Internal execution MAY change; external contract MUST NOT.

---

## Request Schema

`AnswerRequest` (`routes/schemes/nlp.py`):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `text` | `string` | ✅ | — | User question |
| `limit` | `integer` | optional | `8` | Retrieval top-k hint |
| `session_id` | `string` | optional | `null` | Chat continuity |
| `metadata_filter` | `object` | optional | `null` | Pre-retrieval filter |

**Frozen**: Field names, optionality, and defaults MUST NOT change in migration phases 0–3.

---

## Response Schema

### HTTP 200 — Success or Clarification

```json
{
  "signal": "RAG_ANSWER_SUCCESS | RAG_CLARIFICATION_NEEDED",
  "answer": "string",
  "needs_clarification": false,
  "full_prompt": "string | null",
  "chat_history": "array | null"
}
```

### HTTP 400 — No Index

```json
{
  "signal": "RAG_NO_CONTEXT",
  "message": "No indexed documents found for this project. Upload a file and wait for indexing to finish."
}
```

Condition: `not answer and not has_index` (unchanged logic in route).

### HTTP 400 — Answer Error

```json
{
  "signal": "RAG_ANSWER_ERROR",
  "message": "Could not generate an answer. Try rephrasing the question or re-indexing the project."
}
```

Condition: `not answer` with index present.

---

## Signal Enum

`ResponseSignal` values used by this endpoint (MUST remain stable):

| Value | Meaning |
|-------|---------|
| `RAG_ANSWER_SUCCESS` | Answer generated |
| `RAG_CLARIFICATION_NEEDED` | Parser/model requested clarification |
| `RAG_NO_CONTEXT` | No indexed content |
| `RAG_ANSWER_ERROR` | Could not produce answer |

---

## Semantic Compatibility Requirements

Migration MUST preserve these user-visible behaviors:

| Scenario | Expected behavior |
|----------|---------------------|
| Parser disabled | Informative error message (same text as legacy) |
| Clarification needed | `needs_clarification=true`, no retrieval |
| No retrieval results | No-context answer text (language-aware) |
| Field not available | Field-unavailable message listing available fields |
| Session history | Chat messages persisted when `session_id` set |
| Language detection | Arabic/English answer and prompt language |

**Allowed internal differences** (not exposed in API v1):

- Citation structure inside `AnswerResult` (unified has richer citations)
- `plan_id`, `context_id` (internal; may add optional debug header in future — NOT in v1)
- `full_prompt` formatting (MAY differ if unified composer changes layout; monitor in shadow)

---

## Out-of-Scope Endpoints (unchanged in v1)

These continue using legacy `NLPController` retrieval:

| Endpoint | Handler |
|----------|---------|
| `POST .../index` | `index_project` |
| `GET .../index/info` | `get_project_index_info` |
| `POST .../search` | `search_index` |

Document explicitly to prevent scope creep.

---

## Contract Test Checklist

Automated tests MUST assert for each pipeline mode (`legacy`, `shadow`, `unified`):

- [ ] Response JSON schema keys match exactly
- [ ] `signal` value is valid enum member
- [ ] HTTP status codes for no-index / error paths
- [ ] `needs_clarification` consistent with `signal`
- [ ] Request validation errors unchanged (422 on malformed body)

---

## Versioning Policy

Any additive API change (e.g. optional `citations` array in response) requires:

1. New spec / API version bump
2. Default-off until clients opt in
3. NOT part of 015 migration

015 is **strictly non-breaking**.
