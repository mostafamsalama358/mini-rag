# Research: Semantic Query Parser

**Feature**: `004-semantic-query-parser` | **Date**: 2026-07-06

## R1 — Single-stage LLM parser vs current multi-stage pipeline

**Decision**: Replace the entire Query Understanding chain with one `semantic_parse_async` call plus post-parse guardrails.

**Current pipeline cost** (audit):

| Stage | Location | ~LOC / config | Role |
|-------|----------|---------------|------|
| Text normalization | `core/query_understanding.py` | ~80 | Arabic/EN/digits |
| Regex intent classify | `retrieval.yaml` + core | ~200 + YAML | `alternatives`, `exhaustive_list`, … |
| Intent embedding/LLM fallback | core | ~150 | When regex misses |
| Field synonym match | `core/field_resolution.py` + `fields.yaml` | ~450 + YAML | Map query text → concept |
| Catalog fingerprint resolve | `query_rewrite.yaml` + core | ~200 + YAML | Arabic → Latin catalog |
| Entity carry-over | `extract_last_entity` + regex | ~120 + YAML | Follow-up entity |
| Rule-based rewrite | core | ~100 | Prepend entity to query |
| LLM rewrite | core + prompt YAML | ~80 + 20-line prompt | English search query |
| Multi-query variants | core | ~100 | Extra retrieval strings |
| Clarification heuristics | core + YAML | ~150 | Unknown terms |
| Follow-up grounding | `answer_service.py` + YAML | ~200 | Intent-specific retrieval text |

**Total**: ~1,300 SLOC + 365-line `query_rewrite.yaml` + intent blocks in `retrieval.yaml` + synonym lists in `fields.yaml` (duplicated vocabulary).

**Target**:

| Component | ~LOC | Role |
|-----------|------|------|
| `core/query_parser/parser.py` | ~120 | Single LLM call → canonical + QueryPlan |
| `core/query_parser/validator.py` | ~80 | Schema + field registry check |
| `core/query_parser/grounding.py` | ~100 | Catalog entity match |
| `core/query_parser/context.py` | ~60 | Build conversation context |
| `core/query_parser/normalize.py` | ~60 | Pre-parse only |
| `fields/*/parser.yaml` | ~40 each | Prompt + allowed fields + timeouts |

**Rationale**: One vocabulary path (field registry → parser prompt allowed-values → validator). Follow-ups are context input, not regex reference detection.

**Alternatives considered**:
- **Keep regex intents + LLM rewrite** — rejected; dual maintenance, conflicting decisions (spec FR-017).
- **Pure LLM, no grounding** — rejected; entity hallucination fails SC-006.

---

## R2 — Structured output mechanism

**Decision**: Prompt-constrained JSON + Pydantic `QueryPlan` validation + single retry on parse failure. Optional `generate_structured_async` on `LLMInterface` for providers that gain native schema support later.

**Current state**: `LLMInterface` exposes `generate_text` / `generate_text_async` only; no `response_schema` in Vertex/OpenAI/CoHere providers.

**v1 approach**:

```text
1. Build prompt with: field registry concept list, document_language, conversation context, JSON schema excerpt
2. Call generate_text_async(temperature=0, max_output_tokens=256)
3. Extract JSON (markdown fence tolerant)
4. Pydantic validate → QueryPlan
5. On failure: one retry with "return valid JSON only" suffix; else degradation path (spec FR-014)
```

**Rationale**: No provider lock-in; works with existing factory. Constitution G3 preserved.

**Alternatives considered**:
- **Vertex `response_schema` / OpenAI `json_schema`** — defer to v2 provider extension; add optional method on interface without breaking callers.
- **Function calling tools** — heavier; same outcome as JSON schema.
- **Embedding classifier for field** — rejected; reintroduces parallel classification path.

---

## R3 — Field pack configuration: `parser.yaml` replaces `query_rewrite.yaml`

**Decision**: New `parser.yaml` per domain; delete `query_rewrite.yaml` after migration.

**`parser.yaml` shape** (see `data-model.md`):

```yaml
version: 1
timeout_seconds: 2.0
max_output_tokens: 256
temperature: 0.0
document_language: en
context_turn_window: 4
entity_grounding:
  enabled: true
  min_score: 0.82
  metadata_keys: [col_med, brand_name, ...]  # from fields.yaml entity keys
prompt: |
  You are a query parser for {domain_label}. ...
allowed_fields: []  # empty = inject all concepts from fields.yaml at load time
```

**Rationale**: ~90% config reduction (spec SC-005). Prompt carries domain semantics; registry carries allowed field keys.

**Alternatives considered**:
- **Inline prompt in Python** — violates config-driven behavior (constitution field packs).
- **Keep rewrite YAML for fallback** — rejected; spec FR-017.

---

## R4 — Conversation context construction

**Decision**: `build_conversation_context(session_id, chat_history, prior_plans)` produces:

- `current_entity` — from most recent grounded QueryPlan with non-null entity, or explicit mention in latest user turn
- `recent_turns` — last N user/assistant pairs (configurable `context_turn_window`, default 4)
- `document_language` — from `parser.yaml` / project defaults
- `project_domain` — from `project.domain_key`

**Storage**: Persist `QueryPlan` JSON in `chat_messages.metadata` (or equivalent JSON column) on each turn for reliable replay. No re-parsing history with regex.

**Rationale**: Spec FR-015/FR-016; eliminates `extract_last_entity` regex patterns and `is_followup_query` heuristics in `utils/rag_history.py` for entity carry-over (file may remain for unrelated history trimming).

**Alternatives considered**:
- **Re-parse full chat with LLM** — expensive; bounded window sufficient.
- **Regex follow-up detection only** — rejected; spec FR-007.

---

## R5 — Entity grounding strategy

**Decision**: Reuse existing catalog lexicon infrastructure (`ChunkModel.get_distinct_metadata_tokens`, fingerprint index) but move orchestration to `core/query_parser/grounding.py`.

**Flow**:

```text
QueryPlan.entity (raw LLM output)
  → normalize (Latin uppercase for pharmacy)
  → fuzzy match against project catalog (SequenceMatcher + fingerprint, reuse existing index builder)
  → if score < min_score: needs_clarification=true
  → else: replace entity with canonical catalog token
```

**Rationale**: Proven fingerprint approach; only relocation + single call site. Spec FR-012.

**Alternatives considered**:
- **Embedding nearest-neighbor on catalog** — extra latency; fingerprint adequate for drug names.
- **LLM picks from catalog list in prompt** — token budget explodes for large catalogs; grounding post-hoc is cheaper.

---

## R6 — Retrieval integration contract

**Decision**: `answer_service.py` calls parse once, then:

```text
ParseResult
  ├─ needs_clarification → return clarification_prompt (skip retrieval)
  ├─ canonical_query → hybrid search text
  └─ query_plan → retrieval orchestration
        ├─ field → field_resolution.resolve_from_plan(plan) → column keys
        ├─ operation + scope → retrieval limit / exhaustive mode
        ├─ entity → metadata_filter on entity column
        └─ operation=compare → multi-entity path (v1: emit plan; retrieval v1.1)
```

**Delete from answer_service**: `_classify_query_type`, `build_multi_query_variants`, `expand_term_alias_variants`, `resolve_catalog_terms` (pre-parse), `extract_last_entity`, `rule_based_rewrite`, parallel rewrite task, intent-based `wide_retrieval_intents` / `followup_grounding` branches.

**Map operation+scope to retrieval behavior** (replaces intent buckets):

| QueryPlan | Retrieval behavior |
|-----------|-------------------|
| `operation=list, scope=all` | Raise limit to `exhaustive_min_limit`; list output shape |
| `operation=lookup, scope=single` | Default limit; prose output shape |
| `field=interactions` | Use `interaction_column_pairs` from field registry |
| `entity=null, field=unknown` | Canonical query only; no field filter |

**Rationale**: Spec FR-004 — single structured contract.

**Alternatives considered**:
- **Keep intents as parallel signal** — rejected; dual source of truth.
- **Canonical query only, ignore QueryPlan for filters** — rejected; loses deterministic retrieval.

---

## R7 — Migration & feature flag

**Decision**: Strangler fig with `RAG_SEMANTIC_PARSER_ENABLED` env var.

| Stage | Flag | Behavior |
|-------|------|----------|
| P1–P2 | `false` | Old pipeline only; unit test new parser in isolation |
| P3 | `true` (dev) / shadow log | Run new parser, log QueryPlan, still execute old pipeline for answers |
| P4 | `true` (default) | New pipeline only; delete legacy |

Golden-set gate before P4: SC-002/SC-003 thresholds on `tests/golden/query_parser/pharmacy_golden.yaml`.

**Alternatives considered**:
- **Big-bang cutover** — rejected for pharmacy accuracy risk.

---

## R8 — `field_resolution.py` fate

**Decision**: Slim to **plan-driven resolution only** — `resolve_from_plan(query_plan, field_registry, manifest) → FieldResolution`. Remove `resolve_query_field(query_text, ...)` synonym matching from hot path.

Synonym lists in `fields.yaml` become **documentation + parser prompt hints** loaded into allowed field descriptions, not runtime regex/surface-form matching.

**Rationale**: Spec FR-008/FR-018 — one vocabulary, two consumers (parser prompt + retriever mapping).

---

## R9 — Observability

**Decision**: Add Prometheus metric `RAG_PARSE_LATENCY` (histogram, labels: `project_id`, `domain_key`, `outcome=ok|clarify|fallback`). Log fields: `canonical_query`, `query_plan` (JSON), `grounding_score`, `parse_latency_ms`.

**Rationale**: Spec FR-019, constitution G7.

---

## R10 — Testing strategy

**Decision**: Three layers:

1. **Unit** — parser mock LLM, validator, grounding with fixture catalog
2. **Golden** — 50+ pharmacy (question, context) → expected QueryPlan YAML
3. **Integration** — full `answer_question` for EUTHYROX strengths + interaction follow-up against dockerized stack

**Rationale**: Spec FR-020, SC-002/SC-003.
