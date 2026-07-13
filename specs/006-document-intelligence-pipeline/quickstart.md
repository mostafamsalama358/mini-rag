# Quickstart: Validating the Document Intelligence Pipeline

**Feature**: `006-document-intelligence-pipeline`

This guide proves the feature works end-to-end once implemented. It does not duplicate
`data-model.md` or the `contracts/` — it references them and runs against a live stack.

## Prerequisites

- Docker Compose stack up (Postgres + pgvector, broker, Celery worker, API):
  ```powershell
  cd D:\mini-rag
  docker compose -f docker/docker-compose.yml up -d
  ```
- A test project created via the existing API (`POST /api/v1/projects`) — use `domain_key: generic`
  for the baseline checks and `domain_key: pharmacy` for the domain-YAML-only check (US3).
- Fixture files under `tests/fixtures/document_intelligence/` (per `research.md` R10):
  `sample_50_rows.xlsx`, `sample.csv`, `sample_with_table.pdf`, `sample.txt`, plus a malformed
  file for the fallback check.

## 1. Row-completeness check (US1 / SC-001)

1. Upload `sample_50_rows.xlsx` (known 50 data rows) to the test project and trigger processing:
   ```
   POST /api/v1/data/upload/{project_id}
   POST /api/v1/data/process-and-push/{project_id}
   ```
2. Query the `chunks` table (or an admin endpoint) for chunks of this asset where
   `chunk_metadata->>'element_type' = 'table-row'`.
3. **Expect**: exactly 50 such chunks; each `chunk_metadata->>'row_index'` is unique;
   no chunk's `chunk_text` contains a partial row (visually spot-check 2–3).

## 2. One pipeline, four formats (US2)

1. Upload one of each: `sample.txt`, `sample_with_table.pdf`, `sample.csv`, `sample_50_rows.xlsx`.
2. Process all four.
3. **Expect**: all four assets produce chunks whose `chunk_metadata->>'element_type'` is one of
   the canonical vocabulary values from `contracts/document-model-contract.md` — no
   format-specific type strings appear.

## 3. Domain-YAML-only behavior change (US3 / SC-002)

1. Before: note pharmacy project chunking of a table (rows ungrouped, per its shipped
   `element_mapping.table-row: {group: false}`).
2. Add a temporary `fields/manuals/chunking.yaml` per the example in
   `contracts/element-mapping-yaml-contract.md` (grouping `list-item`).
3. Create a project with `domain_key: manuals`, upload a `.txt` fixture with short list items,
   process it.
4. **Expect**: list items are grouped into fewer, larger chunks than the generic default — and
   `git diff` shows **zero changes under `src/core/`** for this behavior change.

## 4. Degraded fallback (US4 / SC-004)

1. Upload the malformed fixture (e.g., a `.xlsx` with a corrupted-but-openable structure that
   yields no rows, or a `.pdf` with unrecoverable OCR text).
2. Process it.
3. **Expect**: ingestion task reports `SUCCESS` (not `FAILURE`); the asset's
   `asset_config->'extraction'->>'outcome'` is `degraded` with a `reason`; at least one
   retrievable chunk exists (whole-document fallback text).
4. Upload a genuinely unreadable file (corrupted beyond opening).
5. **Expect**: ingestion task reports `FAILURE` for that asset (hard failure, not degraded).

## 5. Regression check (SC-003)

Run the existing ingestion regression fixtures (pre-migration baseline) against the new
pipeline:
```powershell
pytest tests/integration/ingestion/test_format_regression.py -v
```
**Expect**: pass rate ≥ pre-migration baseline recorded in this test's fixture comments.

## 6. Answer-quality tie-in (SC-005)

After the above checks pass, re-run the `005-answer-quality` golden runner against the same
fixture project to confirm retrieval coverage (AQ-1) improved on table/list questions:
```powershell
python scripts/run_answer_quality_golden.py --project-id <test_project_id>
```
**Expect**: AQ-1 score on this run ≥ the `005-answer-quality` baseline recorded in
`specs/005-answer-quality/baseline.md`.

## Pass criteria summary

| Check | Section | Success Criteria |
| ----- | ------- | ----------------- |
| Row completeness | 1 | SC-001 |
| Uniform vocabulary across formats | 2 | (US2 acceptance) |
| YAML-only domain diff | 3 | SC-002 |
| Degraded vs hard failure | 4 | SC-004 |
| No format regression | 5 | SC-003 |
| Retrieval coverage improvement | 6 | SC-005 |
