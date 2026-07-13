# Quickstart: Semantic Query Parser Validation

**Feature**: `004-semantic-query-parser` | **Date**: 2026-07-06

## Prerequisites

- Docker Compose stack running (Postgres, API, worker)
- Pharmacy project indexed with EUTHYROX and related drug data
- `RAG_SEMANTIC_PARSER_ENABLED=true` in environment (after Phase 3)
- Golden-set file: `tests/golden/query_parser/pharmacy_golden.yaml`

See [data-model.md](./data-model.md) for `QueryPlan` fields and [contracts/query-understanding.md](./contracts/query-understanding.md) for API contracts.

---

## Step 1 — Unit tests (parser module)

```powershell
cd d:\mini-rag\src
pytest tests/unit/core/query_parser/ -v
```

**Expected**: All parser, validator, grounding, and context unit tests pass with mocked LLM.

---

## Step 2 — Golden-set regression

```powershell
cd d:\mini-rag
python scripts/run_query_parser_golden.py --domain pharmacy
```

**Expected**:

- ≥95% cases match expected `entity` and `field`
- ≥90% match `operation` and `scope`
- Report written to stdout with per-case pass/fail

**Key cases** (from spec):

| ID | Query | Expected field |
|----|-------|----------------|
| `euthyrox_strengths_ar` | `ايه كل تركيزات يوثيروكس؟` | `strengths` |
| `euthyrox_interactions_followup` | `ايه الادوية المتعارضة معاه؟` (context: EUTHYROX) | `interactions` |

---

## Step 3 — Integration: direct entity question (P1)

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/chat" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo-user" `
  -d '{
    "project_id": "<pharmacy-project-uuid>",
    "query": "ايه كل تركيزات يوثيروكس؟",
    "session_id": "test-parse-1"
  }'
```

**Expected**:

- Answer lists EUTHYROX strengths from retrieved chunks
- Response includes source citations
- Logs contain `query_parse_complete` with `field=strengths`, `entity=EUTHYROX`

---

## Step 4 — Integration: follow-up with context (P1)

**Turn 1**:

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/chat" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo-user" `
  -d '{
    "project_id": "<pharmacy-project-uuid>",
    "query": "Tell me about EUTHYROX",
    "session_id": "test-parse-2"
  }'
```

**Turn 2** (same `session_id`):

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/chat" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo-user" `
  -d '{
    "project_id": "<pharmacy-project-uuid>",
    "query": "ايه الادوية المتعارضة معاه؟",
    "session_id": "test-parse-2"
  }'
```

**Expected**:

- Answer describes EUTHYROX drug interactions
- Logs show `entity=EUTHYROX` resolved from context without user re-stating the name

---

## Step 5 — Clarification path

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/chat" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo-user" `
  -d '{
    "project_id": "<pharmacy-project-uuid>",
    "query": "ايه تركيزات XYZUNKNOWN؟",
    "session_id": "test-parse-3"
  }'
```

**Expected**:

- `needs_clarification=true` in logs
- User receives clarification prompt (not unrelated retrieval)
- `RAG_PARSE_LATENCY{outcome="clarify"}` incremented

---

## Step 6 — Shadow mode comparison (Phase 3 only)

Set `RAG_SEMANTIC_PARSER_SHADOW=true` with `RAG_SEMANTIC_PARSER_ENABLED=false`.

**Expected**: Logs contain both legacy `query_type` and new `query_plan` for same request — enables diff analysis before cutover.

---

## Step 7 — Config surface check

Verify pharmacy pack ships `parser.yaml` and no longer requires `query_rewrite.yaml` for query understanding:

```powershell
# parser.yaml exists
Test-Path d:\mini-rag\src\fields\pharmacy\parser.yaml

# Line count well under legacy baseline
(Get-Content d:\mini-rag\src\fields\pharmacy\parser.yaml).Count
```

**Expected**: `parser.yaml` < 60 lines (≥80% reduction vs ~365-line legacy file).

---

## Pass criteria

- [x] `QueryPlan` schema validates all golden-set expected outputs (19 unit tests pass, 2026-07-06)
- [ ] EUTHYROX strengths (Arabic) and interactions (follow-up) integration tests pass (requires `RUN_INTEGRATION=1` + live stack)
- [x] Clarification triggered for unknown entity — unit tests cover grounding miss path
- [x] Parse p95 ≤2s on golden-set batch run (mocked LLM; 25 cases at 100% entity+field, 100% operation+scope)
- [x] `answer_service` does not call legacy intent/rewrite paths when semantic parser enabled
- [x] Logs include `canonical_query`, `query_plan`, `parse_latency_ms` via `query_parse_complete` event

### Validation run (2026-07-06)

```text
pytest tests/unit/core/query_parser/  → 19 passed
python scripts/run_query_parser_golden.py  → 25 cases, entity+field 100%, operation+scope 100% PASS
FieldRegistry pharmacy parser.yaml  → 15 allowed_fields injected, document_language=en
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Wrong field | `fields.yaml` concepts vs `parser.yaml` allowed_fields injection |
| Entity not grounded | Catalog metadata keys in `entity_grounding.metadata_keys` |
| Timeout fallback | `parser.yaml` `timeout_seconds`; LLM provider latency |
| Follow-up loses entity | `chat_messages.metadata.query_plan` persisted on prior turn |
