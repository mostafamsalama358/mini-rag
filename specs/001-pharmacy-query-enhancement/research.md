# Research: Pharmacy Query Enhancement

**Feature**: `001-pharmacy-query-enhancement` | **Date**: 2026-06-29

## R1 — Root Cause of Incomplete Lists

**Decision**: Treat incomplete answers as primarily a **retrieval coverage** problem, secondarily a **generation omission** problem.

**Rationale**: Production failures trace to three code paths:

1. **XLSX chunking** (`ProcessController.get_file_content`) concatenates entire sheets to CSV text, then `RecursiveCharacterTextSplitter` splits by character count (~100–500 chars). Drug rows spanning chunk boundaries are not retrieved together; vector top-k returns only the best-matching chunks.
2. **Exhaustive detection gap** (`is_exhaustive_list_query` in `structural_split.py`) matches legal-document patterns ("اذكر كل شروط المادة") but **not** pharmacy patterns like "كل الادوية المصنفة كباسط للعضلات" or "عايزهم كلهم مهما كان عددهم".
3. **Retrieval limits** default to `limit=8` on answer endpoint and `RAG_RETRIEVAL_CANDIDATES=30`; deduplication by `_source_key` keeps one chunk per file/page/order, hiding additional rows in the same file.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Prompt-only fix ("list everything") | LLM cannot list rows never retrieved in context |
| Increase limit to 200 globally | Wastes tokens on narrow queries; violates budget |
| SQL direct query on Excel | Breaks generic RAG architecture; pharmacy is one domain |

---

## R2 — LLM Query Rewriting Strategy

**Decision**: Add a lightweight **pre-retrieval query understanding step** using the existing `generation_client` with a structured JSON output schema.

**Rationale**: User queries are colloquial Arabic, brand-oriented, and underspecified on follow-ups. Rule-based `build_retrieval_expansion_queries` handles structural/legal patterns only. An LLM rewriter can:

- Map "باسط للعضلات" → search terms: `muscle relaxant`, `MYORELAXANT`, therapeutic class column values
- Map "Cordarone" → `amiodarone`, `CORDARONE`, `كوردارون`
- Expand "عايز كل المتعارضة" → interaction-focused FTS queries targeting `NEWDRUGINTERACTION`
- Resolve follow-ups using last-mentioned drug from chat history

**Schema** (rewrite output):

```json
{
  "intent": "exhaustive_list | drug_detail | interaction_lookup | prescription_check | comparison | general",
  "entities": [{"name": "...", "type": "brand|inn|class", "search_terms": ["..."]}],
  "rewritten_queries": ["..."],
  "retrieval_mode": "standard | exhaustive",
  "target_sources": ["NEWDRUGINTERACTION.xlsx"]
}
```

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Embedding-only query expansion (HyDE) | Less controllable for tabular pharmacy data; harder to test |
| Fine-tuned pharmacy NER model | Higher ops burden; LLM rewrite sufficient for v1 |
| Always run 10 static expansion queries | Wastes embedding calls; not adaptive to intent |

**Guardrails**: Timeout 3s; on failure, fall back to rule-based pharmacy patterns. Rewrite prompt MUST NOT answer the question — only produce search terms.

---

## R3 — Pharmacy Domain Pattern Extensions

**Decision**: Extend `utils/retrieval.py` and `utils/structural_split.py` with pharmacy-specific detectors, co-located in a new `utils/pharmacy/` module to keep domain logic isolated.

**Patterns to add**:

| Pattern (AR / EN) | Intent | Retrieval mode |
|-------------------|--------|----------------|
| `كل الادوية`, `all drugs`, `عايزهم كلهم` | exhaustive_list | exhaustive |
| `متعارض`, `تفاعل`, `interaction`, `conflict` | interaction_lookup | exhaustive |
| `روشتة`, `prescription` + multiple drug tokens | prescription_check | exhaustive |
| `استخدامات`, `جرعة`, `dosage`, `uses` | drug_detail | standard |
| `الفرق بين`, `compare` + 2 drugs | comparison | standard |

**Rationale**: Regex pre-classification is fast, deterministic, and testable; LLM rewrite refines but does not replace it.

---

## R4 — Row-Aware XLSX Chunking

**Decision**: Add **row-per-chunk** (or row-group-of-5) ingestion for `.xlsx` files when `PHARMACY_ROW_CHUNKING=true` or file name matches pharmacy source patterns.

**Rationale**: Each drug row becomes an atomic retrieval unit. FTS can match class columns directly; vector search ranks individual drugs. Eliminates "7 drugs exist but only 1 chunk retrieved" failure mode.

**Format**: Each chunk text = header row + single data row (CSV line), metadata includes `row_index`, `sheet_name`, `source_type: xlsx_row`.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Keep character splitting, raise limit to 100 | Still misses rows in different chunks; token waste |
| External structured DB for pharmacy | Out of scope; user wants generic RAG with pharmacy config |

**Migration**: Re-index required; document in quickstart.

---

## R5 — Prescription Parsing

**Decision**: Rule-based parser first (split on newlines, commas, `tab`, `mg`, brand token patterns), LLM entity extraction as fallback for ambiguous input.

**Rationale**: Prescription input in logs is structured (brand + strength + form per line). Regex handles 80% case; LLM resolves "Cordarone 200 tab" → Cordarone.

**Pairwise retrieval**: For N drugs, generate N interaction sub-queries + N×(N-1)/2 pair queries capped at 15 pairs; merge results.

---

## R6 — Pharmacist Prompt Integration

**Decision**: Store user-authored bilingual pharmacist prompt in `project_prompts` table; align template variable placeholders (`$context`, `$question`) with existing `Template` substitution in `RAGService`.

**Rationale**: Constitution requires prompt versioning in DB, not hard-coded routes. User prompt already defines output sections, medical guidelines, and grounding rules superior to default `rag.py` templates.

**Gap**: Current `RAGService` uses `header_prompt` + `document_prompt` + `footer_prompt` assembly. Pharmacist prompt is a **single system template** with `Context` and `Question` sections. Plan: when `prompt_override` is set, use it as system prompt and map retrieved docs into `$context` / context section; keep document-level citations in API response.

---

## R7 — Generation Completeness for Exhaustive Queries

**Decision**: For `retrieval_mode=exhaustive`:

1. Raise `max_output_tokens` to 8192 (already 4096 for `is_exhaustive_list_query`)
2. Add footer instruction: "You MUST list every matching item from every document. If you stop early, state how many items exist in context vs how many you listed."
3. Optional post-check: count bullet lines vs retrieved row count heuristic; trigger single retry if under-count detected

**Rationale**: Even with full retrieval, LLM may truncate long lists. Explicit completeness instruction + token budget reduces omission.

---

## R8 — Follow-Up Context Resolution

**Decision**: Before query rewrite, inject last user-mentioned drug entity from `select_chat_history_messages` into rewrite prompt when current query lacks drug tokens.

**Rationale**: `RAG_HISTORY_MODE=auto` already selects history for generation; retrieval currently uses raw query only. Adding entity carry-over to rewrite step fixes "الجرعة الخاصة به" without new session storage.

---

## R9 — Observability

**Decision**: Add Prometheus metrics:

- `rag_query_intent_total{intent, project_id}`
- `rag_query_rewrite_latency_seconds`
- `rag_exhaustive_docs_retrieved` histogram

Structured log fields: `intent`, `rewrite_queries_count`, `retrieval_mode`, `entities_extracted`.

---

## R10 — Testing Strategy

**Decision**: Golden-file benchmark from anonymized pharmacy Excel snippets:

| Scenario | Fixture | Expected |
|----------|---------|----------|
| Muscle relaxants list | `fixtures/pharmacy/finalmedicin_sample.xlsx` | N drugs |
| Cordarone interactions | `fixtures/pharmacy/interactions_sample.xlsx` | M interactions |
| 5-drug prescription | synthetic text | K pairwise hits |

Unit tests for regex intent detection and prescription parser. Integration test runs full pipeline against Docker Postgres.
