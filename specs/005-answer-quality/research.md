# Research: Answer Quality Gap (NotebookLM-level Completeness & Accuracy)

**Feature**: `005-answer-quality`  
**Date**: 2026-07-11  
**Goal**: Generic core produces answers that are **complete** (not missing listed items) and **accurate** (faithful to sources), approaching NotebookLM answer quality — without domain-specific Python. Domain differences stay in YAML field packs.

## Product intent (locked)

| Wanted from NotebookLM | Not in scope |
| ---------------------- | ------------ |
| Complete answers | Audio Overview / podcast |
| Exact, source-faithful answers | Mind maps / study guides |
| Generic core + YAML packs | Pharmacy-only code paths |

---

## Success metrics (must be measurable)

Numbers below are **targets**. Baseline is unknown until the eval harness (T003) runs once on a fixed fixture project.

| ID | Metric | Definition | Target |
| -- | ------ | ---------- | ------ |
| **AQ-1** | Retrieval coverage | For exhaustive/list gold cases: `|retrieved ∩ gold_source_rows| / |gold_source_rows|` before generation | ≥ **95%** |
| **AQ-2** | List completeness | For list answers: `|answer_items ∩ gold_items| / |gold_items|` | ≥ **95%** |
| **AQ-3** | Hallucination / invent rate | Share of answer claims not supported by retrieved context (human or LLM-judge on golden set) | ≤ **5%** |
| **AQ-4** | Unsupported silence | When gold says “not in sources”, system refuses or clarifies instead of inventing | **100%** |
| **AQ-5** | Truncation rate | Exhaustive queries where char-budget or rerank drops >20% of retrieved candidates before prompt | ≤ **10%** |
| **AQ-6** | Citation usefulness | Answer ends with Sources; cited labels correspond to chunks actually used | ≥ **90%** of cases |

**Eval unit**: one case = `(question, optional chat context, gold_items or gold_claims, gold_source_keys)`.  
Schema is **domain-agnostic**; fixtures live under pack folders (e.g. pharmacy) but the scorer lives in `core` / `scripts`.

---

## Current pipeline strengths (keep)

Already in core / packs (004 + field registry):

1. Semantic `QueryPlan` → structured retrieval intent (entity, field, operation, scope).
2. Exhaustive limit bump when `operation=list` + `scope=all` (`exhaustive_min_limit` from `retrieval.yaml`).
3. Entity grounding (catalog + document-level).
4. Clarification on unknown entity (no silent wrong retrieval).
5. Hybrid search + rerank + citations prompt language.
6. Domain prompts via `fields/*/prompts/` + generic `rag.py` system rules for “list every item”.

---

## Gap analysis (why results are still “incomplete / imprecise”)

### G1 — No coverage gate after retrieval (primary incompleteness)

**Symptom**: List questions miss items that exist in the index.  
**Cause**: Top-k / RRF / rerank return a subset; nothing compares retrieved count to **candidate row count** for the entity/field.  
**Where**: `answer_service.py` retrieval stage; `count_entity_prefix_matches` is logged but not used as a top-up signal.  
**Fix (core)**: If `scope=all` (or list-shaped field) and `candidate_rows > len(docs)`, fetch remaining entity-scoped rows (or raise limit and re-search) before generation.

### G2 — Context truncation after successful retrieval

**Symptom**: Retrieved 80 rows; prompt only keeps first N by `RAG_PROMPT_CHAR_BUDGET`.  
**Cause**: Budget loop drops tail docs silently (`answer_service.py`).  
**Fix (core)**: Prefer packing more shorter field values; log `truncated=true`; for exhaustive mode, raise budget or multi-pass generate (map-reduce lists) instead of silent drop.

### G3 — Reranker can discard exhaustive recall

**Symptom**: Correct rows retrieved, then rerank empties or heavily prunes the set.  
**Cause**: Rerank optimized for “best passage”, not “all matching rows”.  
**Fix (core)**: Exhaustive mode: rerank for ordering only, **do not cut** below `min(candidate_rows, retrieval_limit)`; or skip rerank cut for `scope=all`.

### G4 — Generation may omit items still in context

**Symptom**: All rows in prompt; model lists a subset.  
**Cause**: Known LLM list truncation (001 research R7); no under-count retry.  
**Fix (core)**: Completeness footer + heuristic count (bullets / distinct values vs retrieved row count) → one retry with stronger instruction.

### G5 — No answer-quality golden harness

**Symptom**: Parser golden set exists (004); answer completeness is not regression-tested.  
**Fix (core)**: `tests/golden/answer_quality/` + `scripts/run_answer_quality_golden.py` scoring AQ-1…AQ-6.

### G6 — Domain hooks still in Python

**Symptom**: `if query_plan.field == "interactions"` hard-coded (limit 500, structured fetch).  
**Cause**: Fast pharmacy path without YAML strategy.  
**Fix (core + YAML)**: `retrieval.yaml` strategy keys (`structured_pair`, `entity_prefix_all`, `vector_default`); core dispatches by strategy name — packs only declare which concept uses which strategy.

### G7 — Chunk focus can strip list detail

**Symptom**: `focus_document_text_for_query` keeps a slice; other list items in the same chunk disappear.  
**Fix (core)**: Disable focus when `scope=all` or `output_shape=list` (honor `disable_chunk_focus` already; make plan-driven default).

### G8 — Faithfulness not verified

**Symptom**: Fluent answer with invented numbers/names.  
**Cause**: Prompt says “documents only”; no post-check.  
**Fix (core, optional v1)**: Lightweight claim check against context for numeric / entity tokens; on fail, regenerate or soften to “not found”.

---

## Architectural verdict

| Approach | Verdict |
| -------- | ------- |
| More pharmacy regex / special cases | Reject — fights generic core goal |
| Bigger prompts only | Insufficient — cannot list what was never retrieved |
| **Core completeness + faithfulness pipeline + YAML strategies** | Preferred |
| Stuff entire corpus every turn (NotebookLM-style) | Too expensive; use **coverage-gated exhaustive retrieve** instead |

NotebookLM-like quality here means: **almost all relevant indexed facts for the question reach the model, and the model is forced to use them faithfully** — not a clone of NotebookLM UX.

---

## Baseline measurement plan (before claiming %)

1. Build one fixture project (pharmacy pack OK for fixtures; scorers stay generic).
2. Curate ≥20 list cases + ≥15 factual cases + ≥10 “not in sources” cases.
3. Run scorer once → fill **Baseline** column in a results table under `specs/005-answer-quality/baseline.md`.
4. Implement G1–G4; re-run; gate merges on AQ-1/AQ-2/AQ-3 targets.

---

## Out of scope

- Audio / mind-map / study-guide product features  
- Fine-tuning a custom model  
- Replacing hybrid retrieval architecture  
- Pack-specific Python modules under `utils/{domain}/`
