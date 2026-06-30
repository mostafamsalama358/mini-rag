# Data Model: Pharmacy Query Enhancement

**Feature**: `001-pharmacy-query-enhancement` | **Date**: 2026-06-29

## Overview

This feature introduces **transient domain objects** for query understanding and retrieval planning. No new persistent database tables are required beyond existing `project_prompts`. Optional chunk metadata extensions apply to `DataChunk.chunk_metadata` JSON.

---

## Entities

### QueryIntent

Represents classified user intent before retrieval.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `intent` | enum | yes | `exhaustive_list`, `drug_detail`, `interaction_lookup`, `prescription_check`, `comparison`, `general` |
| `confidence` | float | yes | 0.0–1.0; rule-based = 1.0, LLM = model confidence or 0.8 default |
| `original_query` | str | yes | Raw user input |
| `language` | str | yes | `ar` or `en` (from `detect_query_language`) |
| `entities` | list[PharmacyEntity] | no | Extracted drugs, classes, ingredients |
| `rewritten_queries` | list[str] | yes | Retrieval-optimized search strings (min 1 = original) |
| `retrieval_mode` | enum | yes | `standard` or `exhaustive` |
| `target_sources` | list[str] | no | Hint file names (e.g., `NEWDRUGINTERACTION.xlsx`) |
| `prescription_drugs` | list[str] | no | Parsed drug names for prescription_check intent |

**Validation**:
- `rewritten_queries` MUST contain at least the normalized original query
- `retrieval_mode=exhaustive` REQUIRES `intent` in (`exhaustive_list`, `interaction_lookup`, `prescription_check`)
- `prescription_drugs` REQUIRED when `intent=prescription_check`

**State transitions**: Created per request; not persisted.

---

### PharmacyEntity

Normalized reference to a drug, class, or ingredient.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `surface_form` | str | yes | Text as it appeared in query |
| `entity_type` | enum | yes | `brand`, `inn`, `class`, `form`, `unknown` |
| `search_terms` | list[str] | yes | Terms for vector + FTS retrieval |
| `normalized_name` | str | no | Canonical name if resolved |

**Validation**:
- `search_terms` non-empty
- Each term length ≥ 2 characters (except INN abbreviations)

---

### RetrievalPlan

Orchestration blueprint produced by query understanding.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `primary_query` | str | yes | Original user query |
| `queries` | list[RetrievalQuery] | yes | Ordered search passes |
| `merge_strategy` | enum | yes | `rrf` (default) |
| `dedupe_by` | enum | yes | `source_key` for standard; `text_prefix` for exhaustive xlsx rows |
| `post_enrichment` | bool | yes | Whether to run chunk continuation enrichment |

### RetrievalQuery (value object)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | str | yes | Search string |
| `limit` | int | yes | Per-pass candidate limit |
| `metadata_filter` | dict | no | e.g., `{"file_name": "NEWDRUGINTERACTION.xlsx"}` |
| `source` | enum | yes | `original`, `rewrite`, `rule_expansion`, `pairwise` |

**Limit rules**:

| retrieval_mode | Per-query limit | Total candidate cap |
|----------------|-----------------|---------------------|
| `standard` | `max(limit, 12)` | 30 |
| `exhaustive` | `max(limit, 50)` | 150 |
| `prescription_check` | 30 per pair | 200 |

---

### ProjectPrompt (existing — extended usage)

Existing table `project_prompts`; no schema change.

| Field | Type | Description |
|-------|------|-------------|
| `prompt_id` | int | PK |
| `project_id` | int | FK → projects |
| `prompt_en` | text | English pharmacist system template |
| `prompt_ar` | text | Arabic pharmacist system template |

**Template placeholders** (new convention):

| Placeholder | Substituted by |
|-------------|--------------|
| `$context` or `NULL` in Context section | Joined retrieved document text |
| `$question` or `NULL` in Question section | User query |
| `$doc_count` | Number of retrieved documents used |

**Versioning**: Each update replaces row; future enhancement may add `version` column (out of scope v1).

---

### DataChunk Metadata Extensions (JSON — optional)

Applied during XLSX row chunking; stored in existing `chunk_metadata` JSONB.

| Field | Type | Description |
|-------|------|-------------|
| `row_index` | int | 0-based row in sheet |
| `sheet_name` | str | Excel sheet name |
| `chunking_strategy` | str | `xlsx_row` when row-aware |
| `drug_class` | str | Optional parsed class column |
| `active_ingredient` | str | Optional parsed INN column |
| `brand_name` | str | Optional parsed brand column |

**Relationships**: Chunk belongs to Asset; Asset belongs to Project. No new FKs.

---

## Relationships Diagram

```text
Project 1──1 ProjectPrompt
Project 1──* Asset 1──* DataChunk (metadata may include pharmacy fields)

[Per request]
User Query → QueryIntent → RetrievalPlan → list[RetrievedDocument] → Answer
```

---

## Validation Rules Summary

1. Query rewrite output MUST be valid JSON; invalid → fallback to rule-based `QueryIntent`
2. Exhaustive retrieval MUST NOT apply `focus_document_text_for_query` (would hide rows)
3. Prescription parser MUST deduplicate drug names case-insensitively
4. Pairwise interaction queries capped at 15 pairs per request (configurable `PHARMACY_MAX_PAIR_QUERIES`)
5. API `limit` parameter overridden upward when `retrieval_mode=exhaustive` (minimum 50)
