# Answer Quality — Baseline Scores

**Feature**: `005-answer-quality`  
**Status**: Partial — Document Intelligence (006) post-migration AQ-1 proxy recorded

| Metric | Target | Baseline (pre-fix) | Post Phase 2–4 / post-006 |
|--------|--------|---------------------|---------------------------|
| AQ-1 Retrieval coverage | ≥95% | _TBD_ (005 harness pending) | **100%** proxy: 50/50 `table-row` chunks indexed from `sample_50_rows.xlsx` (project_id=1, 2026-07-13) |
| AQ-2 List completeness | ≥95% | _TBD_ | _TBD_ |
| AQ-3 Hallucination rate | ≤5% | _TBD_ | _TBD_ |
| AQ-4 Unsupported silence | 100% | _TBD_ | _TBD_ |
| AQ-5 Truncation rate | ≤10% | _TBD_ | _TBD_ |
| AQ-6 Citation usefulness | ≥90% | _TBD_ | _TBD_ |

**Fixture set**: `tests/fixtures/document_intelligence/` (50-row xlsx + csv/txt/pdf)  
**Date / commit**: 2026-07-13 — via `scripts/validate_document_intelligence_quickstart.py`  
**Note**: Full `scripts/run_answer_quality_golden.py` harness from 005 is not implemented yet; AQ-1 above is structural retrieval-coverage proxy (indexed row completeness), which is the prerequisite SC-005 signal for 006.
