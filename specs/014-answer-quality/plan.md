# Plan: Answer Quality (NotebookLM-level Completeness & Accuracy)

**Branch**: `005-answer-quality`  
**Date**: 2026-07-11  
**Status**: Planned (T000 blocker fixed in tree)

## Summary

Close the gap between “RAG that sometimes misses rows / invents details” and **NotebookLM-like answer quality**: complete and faithful answers from indexed sources. Architecture stays **generic core + YAML packs**.

## Approach

1. **Measure** with a domain-agnostic golden harness (AQ-1…AQ-6).
2. **Retrieve enough**: coverage gate + exhaustive rerank policy + no destructive chunk focus on lists.
3. **Pack & generate completely**: budget-aware packing + under-count retry.
4. **Stay faithful**: optional claim check + refusal path.
5. **De-specialize Python**: YAML `retrieval_strategy` instead of `if field == "interactions"`.

## Key code touchpoints

| Area | Path |
| ---- | ---- |
| Orchestration | `src/services/rag/answer_service.py` |
| Exhaustiveness | `src/core/retrieval/exhaustiveness.py` (new) |
| Quality helpers | `src/core/answer_quality/` (new) |
| Profiles | `src/fields/schemas.py`, `src/fields/generic/retrieval.yaml` |
| Prompts | `src/stores/llm/templates/locales/*/rag.py` |
| Eval | `tests/golden/answer_quality/`, `scripts/run_answer_quality_golden.py` |

## Dependencies

- `004-semantic-query-parser` — `QueryPlan` + clarification path  
- `002-field-registry` — packs, `FieldResolution`, manifests  

## Success

Merge when golden runner meets targets in `research.md` (or documents justified shortfalls with owners). UX clones of NotebookLM are explicitly out of scope.
