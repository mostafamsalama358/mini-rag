# Data Model: Semantic Query Parser

**Feature**: `004-semantic-query-parser` | **Date**: 2026-07-06

## Runtime entities (new)

### `QueryPlan`

Structured retrieval intent — **the contract between parser and retriever**.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `entity` | `string \| null` | yes | If non-null, must pass grounding or trigger clarification | Canonical catalog identifier for primary subject |
| `entities` | `string[]` | no | Each entry grounded when present | Multi-entity operations (compare, interaction-between) |
| `field` | `string` | yes | Must be in field registry OR literal `unknown` | Registry-backed concept key |
| `operation` | enum | yes | `lookup` \| `list` \| `compare` \| `explain` \| `count` \| `unsupported` | User intent verb |
| `scope` | enum | yes | `all` \| `single` \| `subset` | Exhaustive vs focused |
| `language` | `string` | yes | ISO 639-1 | Document language for canonical query |
| `filters` | `object` | no | Domain-defined keys only | Qualifiers (strength value, dosage form, …) |
| `confidence` | `float` | no | 0.0–1.0 | Parser self-assessment |
| `needs_clarification` | `bool` | yes | default `false` | When true, skip retrieval |
| `clarification_prompt` | `string` | no | Required if `needs_clarification=true` | User-facing message |

**Pydantic location**: `core/query_parser/schema.py`

**Example** (EUTHYROX strengths):

```json
{
  "entity": "EUTHYROX",
  "field": "strengths",
  "operation": "list",
  "scope": "all",
  "language": "en",
  "needs_clarification": false
}
```

**State transitions**:

```text
[raw user text]
    → pre_normalize()
    → llm_parse()
    → validate_schema()        ──fail──► retry once ──fail──► fallback plan
    → validate_field_registry() ──fail──► needs_clarification OR field=unknown
    → ground_entity()          ──fail──► needs_clarification=true
    → [ready QueryPlan]
```

---

### `CanonicalQuery`

Not a separate persisted entity — a `str` field on `ParseResult`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `text` | `string` | Document-language retrieval string |

**Example**: `"List all drug interactions of EUTHYROX."`

---

### `ConversationContext`

Bounded input to the semantic parser.

| Field | Type | Required | Source |
|-------|------|----------|--------|
| `current_entity` | `string \| null` | yes | Prior grounded QueryPlan or explicit mention |
| `recent_turns` | `TurnSummary[]` | yes | Chat history (last N turns) |
| `document_language` | `string` | yes | `parser.yaml` / project defaults |
| `project_domain` | `string` | yes | `project.domain_key` |

**`TurnSummary`**:

| Field | Type | Description |
|-------|------|-------------|
| `user_text` | `string` | Original user message |
| `canonical_query` | `string \| null` | Prior parse output |
| `query_plan` | `QueryPlan \| null` | Prior structured plan |

---

### `ParseResult`

Output of `semantic_parse_async`.

| Field | Type | Description |
|-------|------|-------------|
| `original_query` | `string` | User input after pre-normalization |
| `canonical_query` | `string` | Document-language search text |
| `query_plan` | `QueryPlan` | Structured intent |
| `used_llm` | `bool` | Whether LLM succeeded |
| `latency_ms` | `float` | Parse stage duration |
| `grounding_score` | `float \| null` | Entity match confidence |
| `error` | `string \| null` | Degradation reason if fallback |

---

### `ParserProfile`

Loaded from `fields/{domain}/parser.yaml` — replaces `QueryRewriteProfile` for query understanding.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | `int` | `1` | Schema version |
| `timeout_seconds` | `float` | `2.0` | Hard parse timeout |
| `max_output_tokens` | `int` | `256` | LLM output cap |
| `temperature` | `float` | `0.0` | Generation temperature |
| `document_language` | `string` | `en` | Target canonical language |
| `context_turn_window` | `int` | `4` | Max history turns in context |
| `prompt` | `string` | required | Parser system prompt template |
| `allowed_fields` | `string[]` | `[]` | Override field list; empty = all registry concepts |
| `entity_grounding` | `GroundingConfig` | see below | Catalog match settings |

**`GroundingConfig`**:

| Field | Type | Default |
|-------|------|---------|
| `enabled` | `bool` | `true` |
| `min_score` | `float` | `0.82` |
| `metadata_keys` | `string[]` | from `fields.yaml` entity keys |

**Pydantic location**: `fields/schemas.py` → `ParserProfile`

**Merge precedence** (same as other field-pack modules):

```text
effective_parser = merge(generic.parser, domain.parser, project.config_json.parser?)
```

---

## Field registry relationship

`fields.yaml` concepts remain authoritative for **allowed `field` values** and **column mapping**:

```text
fields.yaml concepts[].concept  →  QueryPlan.field allowed values
fields.yaml concepts[].resolves_to_columns  →  retrieval column filter
fields.yaml concepts[].output_shape  →  answer formatting hint (list vs prose)
```

Synonym lists in `fields.yaml` are **no longer used for runtime query-text matching**. They may be injected into parser prompt as human-readable field descriptions.

---

## Persistent storage changes

### `chat_messages` — extend metadata (recommended)

Store parse artifacts per turn for context replay and debugging.

| Metadata key | Type | Description |
|--------------|------|-------------|
| `query_plan` | `object` | Grounded QueryPlan JSON |
| `canonical_query` | `string` | Canonical query text |
| `parse_latency_ms` | `float` | Optional telemetry |

**Migration**: Alembic not required if `chat_messages` already has JSON `metadata` column. If absent, add nullable `metadata JSONB DEFAULT '{}'` in implementation phase.

---

## Entity catalog (derived, not new table)

**`CatalogEntry`** — runtime cache per project, built from chunk metadata.

| Field | Type | Source |
|-------|------|--------|
| `canonical_id` | `string` | Primary entity metadata value |
| `aliases` | `string[]` | All metadata key variants for same row |
| `fingerprint` | `string` | Normalized match key |

Built via existing `ChunkModel.get_distinct_metadata_tokens` + `build_catalog_fingerprint_index` (relocated to `grounding.py`).

---

## Deprecated entities (removed from hot path)

| Legacy | Replacement |
|--------|-------------|
| `IntentResult` / regex intents | `QueryPlan.operation` + `QueryPlan.field` |
| `RewriteResult` | `ParseResult.canonical_query` |
| `RewriteConfig` / `query_rewrite.yaml` | `ParserProfile` / `parser.yaml` |
| `EntityExtractionConfig` | `ConversationContext.current_entity` |
| `resolve_query_field(query_text)` | `resolve_from_plan(query_plan)` |
| `query_type` string in answer_service | Derived from `QueryPlan.operation` + `scope` |

---

## Retrieval mapping table

| QueryPlan signal | Retrieval parameter |
|------------------|---------------------|
| `canonical_query` | `text` for hybrid search |
| `entity` | `metadata_filter` on entity column |
| `field` → `FieldResolution` | column boost / filter |
| `operation=list, scope=all` | `limit = exhaustive_min_limit` |
| `operation=compare` | multi-entity expansion (v1.1) |
| `needs_clarification=true` | skip retrieval |

---

## Configuration surface comparison

| Artifact | Before | After |
|----------|--------|-------|
| `query_rewrite.yaml` | ~365 lines pharmacy | **deleted** |
| `parser.yaml` | — | ~40 lines |
| Intent blocks in `retrieval.yaml` | ~80 lines patterns | **removed from UW path** (retrieval expansion patterns may remain) |
| `fields.yaml` synonyms | runtime matching | prompt hints only |
| `core/query_understanding.py` | ~1,319 LOC | **deleted** (60 LOC normalize retained) |
