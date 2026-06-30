# Quickstart: Pharmacy Query Enhancement Validation

**Feature**: `001-pharmacy-query-enhancement` | **Date**: 2026-06-29

## Prerequisites

- Docker Compose stack running (Postgres + pgvector, API, Celery worker)
- Pharmacy Excel files indexed: `FINALMEDICIN.xlsx`, `NEWDRUGINTERACTION.xlsx`, `ALLMATERIAL1.xlsx`
- Environment variables:

```env
RAG_ENABLE_HYBRID_SEARCH=true
RAG_ENABLE_RERANKER=true
RAG_RETRIEVAL_CANDIDATES=50
PHARMACY_QUERY_REWRITE_ENABLED=true
PHARMACY_ROW_CHUNKING=true
```

After enabling `PHARMACY_ROW_CHUNKING`, **re-index** the pharmacy project (see Step 1).

---

## Step 1 — Re-index Pharmacy Project

```powershell
# Push re-index task (replace PROJECT_ID)
curl -X POST "http://localhost:8000/api/v1/nlp/index/push/PROJECT_ID" `
  -H "Content-Type: application/json" `
  -d '{"do_reset": 1}'
```

Wait until index info shows `is_fully_indexed: true`:

```powershell
curl "http://localhost:8000/api/v1/nlp/index/info/PROJECT_ID"
```

**Expected**: `record_count` > 0, `chunk_count` increases vs character-chunked baseline (one chunk per Excel row).

---

## Step 2 — Configure Pharmacist Prompt

Store the bilingual pharmacist prompt via project prompt API or admin UI. Verify `prompt_ar` and `prompt_en` contain Context/Question placeholders.

**Expected**: Answers use # الملخص / # التفاصيل structure for Arabic queries.

---

## Step 3 — Exhaustive Drug Class List

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/index/answer/PROJECT_ID" `
  -H "Content-Type: application/json" `
  -d '{"text": "كل الادوية المصنفة كباسط للعضلات", "limit": 50}'
```

**Expected**:
- Answer lists **all** muscle relaxants present in `FINALMEDICIN.xlsx` (compare count manually against source file)
- `# تغطية المصدر` section shows document count > 1
- Re-running produces identical drug set

**Failure indicator**: Only 1–2 drugs when source has 7+.

---

## Step 4 — Complete Interaction Lookup

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/index/answer/PROJECT_ID" `
  -H "Content-Type: application/json" `
  -d '{"text": "عايز كل الادوية المتعارضة مع cordarone", "limit": 50}'
```

**Expected**:
- All documented Cordarone/amiodarone interactions from `NEWDRUGINTERACTION.xlsx`
- Severity / risk included when present in retrieved chunks
- No contradiction with a second identical request

Follow-up test:

```powershell
# Same session_id as above
curl -X POST "http://localhost:8000/api/v1/nlp/index/answer/PROJECT_ID" `
  -H "Content-Type: application/json" `
  -d '{"text": "عايزهم كلهم مهما كان عددهم", "limit": 50, "session_id": "SESSION_UUID"}'
```

**Expected**: Count does not decrease vs first answer.

---

## Step 5 — Prescription Cross-Check

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/index/answer/PROJECT_ID" `
  -H "Content-Type: application/json" `
  -d @- << 'EOF'
{
  "text": "عندى روشتة وعايزك تساعدنى فى تحديد الادوية المتعرضة مع بعض\nCordarone 200 tab\nTryptizol 25 mg tab\nAverozolid 600 tab\nLyrica 75 mg tab\nAlkapress 10 mg",
  "limit": 50
}
EOF
```

**Expected**:
- Each drug identified or marked unavailable
- Pairwise interactions listed **only** when documented
- No generic warnings unrelated to the specific drugs (e.g., "cold medicines") unless in retrieved context for those drugs

---

## Step 6 — Drug Detail Follow-Up

Use a shared `session_id` across requests.

**Turn 1**:
```json
{"text": "dimra استخدامات", "session_id": "test-session-001", "limit": 20}
```

**Turn 2**:
```json
{"text": "الجرعة الخاصة به", "session_id": "test-session-001", "limit": 20}
```

**Expected**: Turn 2 retrieves Dimra dosage info without user repeating the drug name.

---

## Step 7 — Retrieval Debug (Search Endpoint)

Inspect raw retrieval before generation:

```powershell
curl -X POST "http://localhost:8000/api/v1/nlp/index/search/PROJECT_ID" `
  -H "Content-Type: application/json" `
  -d '{"text": "muscle relaxant MYORELAXANT", "limit": 30}'
```

**Expected**: Multiple distinct rows from `FINALMEDICIN.xlsx` with `metadata.chunking_strategy = xlsx_row` when row chunking enabled.

---

## Step 8 — Metrics Check

```powershell
curl "http://localhost:8000/metrics" | Select-String "rag_query_intent"
```

**Expected**: `rag_query_intent_total{intent="exhaustive_list"}` increments after Step 3.

---

## Pass/Fail Summary

| Scenario | Pass criteria |
|----------|---------------|
| Exhaustive class list | ≥95% row recall vs source file |
| Interaction lookup | Stable count across repeats; ≥95% recall |
| Prescription check | Documented pairs only; no hallucinated interactions |
| Follow-up dose | Correct drug resolved from history |
| Safety | No start/stop/change medication advice |

See [data-model.md](./data-model.md) for entity definitions and [contracts/](./contracts/) for API schemas.
