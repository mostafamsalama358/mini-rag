# Implementation Plan: Semantic Query Parser

**Branch**: `004-semantic-query-parser` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-semantic-query-parser/spec.md`

## Summary

Replace the current multi-stage Query Understanding pipeline (~1,300 SLOC in `core/query_understanding.py`, 365-line `query_rewrite.yaml`, regex intents in `retrieval.yaml`, parallel `field_resolution` synonym matching, follow-up heuristics) with a **single semantic parsing stage** that produces:

1. **Canonical Query** — document-language retrieval text
2. **QueryPlan** — schema-validated structured intent consumed exclusively by retrieval for filters/scope

Architecture: **LLM-first semantic parser** + **thin deterministic guardrails** (pre-parse normalization, Pydantic schema validation, field-registry validation, catalog entity grounding). No preservation of legacy regex intent trees or rewrite YAML blocks.

Implementation ships in **4 phases**: schema & parser core → grounding & validation → retrieval integration → legacy removal & golden-set validation.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic v2, existing `LLMProviderFactory` generation clients, `FieldRegistry`

**Storage**: PostgreSQL + pgvector (unchanged); project entity catalog derived from chunk metadata (existing `ChunkModel.get_distinct_metadata_tokens`)

**Testing**: pytest + pytest-asyncio; unit tests for parser/validator/grounding; integration tests for answer pipeline; golden-set regression file for QueryPlan accuracy

**Target Platform**: Linux server (Docker); local dev via Docker Compose

**Project Type**: Web service (FastAPI) + Celery workers + static SPA

**Performance Goals**: Parse stage p95 ≤2s (spec NFR-002); end-to-end answer latency flat or improved vs current multi-stage pipeline

**Constraints**:
- Retriever MUST treat QueryPlan as sole structured filter source (spec FR-004)
- Parser core MUST remain domain-agnostic; vocabulary in `fields/{domain}/` only
- No new regex intent layers; pre-parse normalization limited to Unicode/digits/whitespace
- Golden-set: ≥95% entity+field accuracy on 50 pharmacy cases

**Scale/Scope**:
- Delete/replace ~1,300 SLOC `core/query_understanding.py` (keep only `normalize.py` extract)
- Retire pharmacy `query_rewrite.yaml` (~365 lines) → slim `parser.yaml` (~40 lines)
- Touch `answer_service.py` (primary integration), `FieldRegistry`, `fields/schemas.py`, retrieval search path
- Out of scope: reranking, answer generation, hybrid fusion algorithms

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Parser in `core/query_parser/` (domain-agnostic); orchestration in `services/rag/`; catalog I/O via `repositories/`; field vocabulary in `fields/` | ☑ |
| G2 Feature-First | Feature slice: parser module + answer pipeline integration + field-pack config + tests co-located under feature spec | ☑ |
| G3 SOLID / Plugins | LLM access via existing `generation_client` interface; optional `generate_structured_async` extension on `LLMInterface`; no provider imports in core parser | ☑ |
| G4 Async + Types | `semantic_parse_async` on hot path; `QueryPlan` / `ParseResult` Pydantic models; public APIs fully typed | ☑ |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations unchanged; only upstream query contract changes | ☑ |
| G6 Testing | Golden-set regression + unit tests for validator/grounding + integration test for EUTHYROX scenarios | ☑ |
| G7 Observability | Log canonical query, QueryPlan, grounding outcome, parse latency; extend metrics with `RAG_PARSE_LATENCY` | ☑ |
| G8 Security | No secrets in parser prompts; catalog grounding uses parameterized repository queries | ☑ |
| G9 Performance | Parse is async with hard timeout; catalog lexicon cached per project (reuse existing pattern) | ☑ |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker — unchanged | ☑ |

## Project Structure

### Documentation (this feature)

```text
specs/004-semantic-query-parser/
├── plan.md              # This file
├── research.md          # Phase 0: parser design decisions
├── data-model.md        # Phase 1: QueryPlan, context, config entities
├── quickstart.md        # Phase 1: validation runbook
├── contracts/           # Phase 1: parser + retrieval contracts
│   └── query-understanding.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root) — TARGET structure

```text
src/
├── core/
│   ├── query_parser/                 # NEW — replaces query_understanding.py
│   │   ├── __init__.py               # public: semantic_parse_async, ParseResult
│   │   ├── schema.py                 # QueryPlan, ConversationContext, ParseResult
│   │   ├── normalize.py              # pre-parse only (extracted from legacy)
│   │   ├── context.py                # build context from chat history
│   │   ├── parser.py                 # LLM semantic parse + timeout/retry
│   │   ├── validator.py              # field-registry + schema validation
│   │   └── grounding.py              # catalog entity fuzzy match
│   ├── field_resolution.py           # SLIM — maps QueryPlan.field → columns (no synonym match)
│   └── retrieval/                    # ADAPT — accept QueryPlan in search orchestration
├── fields/
│   ├── schemas.py                      # ADD ParserProfile; DEPRECATE QueryRewriteProfile
│   ├── generic/parser.yaml             # NEW — default parser prompt + settings
│   └── pharmacy/
│       ├── parser.yaml                 # NEW — replaces query_rewrite.yaml
│       └── query_rewrite.yaml          # DELETE after migration
├── services/
│   ├── FieldRegistry.py                # load parser.yaml; expose parser_profile on FieldProfile
│   └── rag/
│       └── answer_service.py           # REPLACE multi-stage UW with single parse call
└── tests/
    ├── unit/core/query_parser/         # parser, validator, grounding, context
    ├── integration/rag/                # EUTHYROX strength + interaction follow-up
    └── golden/query_parser/            # pharmacy_golden.yaml + runner

scripts/
└── run_query_parser_golden.py          # golden-set evaluation CLI
```

**Structure Decision**: Single-project layout under existing `src/`. New `core/query_parser/` package is the bounded Query Understanding stage. `answer_service.py` becomes the composition root that calls `semantic_parse_async` then passes `QueryPlan` to retrieval. Legacy `core/query_understanding.py` deleted in Phase 4.

## Phase Overview

| Phase | Goal | Key deliverables | Risk |
|-------|------|------------------|------|
| **P1** Schema & parser core | QueryPlan model + LLM parse with timeout | `schema.py`, `parser.py`, `parser.yaml`, unit tests | Medium — structured output reliability |
| **P2** Guardrails | Validation + grounding + context | `validator.py`, `grounding.py`, `context.py` | Low |
| **P3** Retrieval integration | Wire QueryPlan into answer pipeline | `answer_service.py`, retrieval search, field_resolution slim | High — behavior change |
| **P4** Legacy removal | Delete old pipeline; golden-set gate | Remove `query_understanding.py`, `query_rewrite.yaml`, intent regex usage in UW | Medium — regression |

Feature flag `RAG_SEMANTIC_PARSER_ENABLED` (default `true` after P4) allows shadow-mode comparison during P3.

## Complexity Tracking

> No constitution violations. Design intentionally reduces complexity vs current pipeline.

| Decision | Why not simpler | Rejected alternative |
|----------|-----------------|---------------------|
| Keep catalog grounding (deterministic) | LLM alone hallucinates entities (spec SC-006) | Pure LLM-only — fails pharmacy safety bar |
| Keep field registry validation | Parser may emit plausible but unindexed fields | Trust LLM field output — breaks retrieval filters |
| Extend LLMInterface vs prompt-only JSON | Typed contract + future native schema support | Regex JSON extract only — fragile at scale |
| Feature flag during P3 | Compare golden-set before cutover | Big-bang swap — too risky for live pharmacy |

## Post-Design Constitution Re-check

All gates remain ☑ after Phase 1 design. No inward infrastructure imports in `core/query_parser/`. RAG downstream stages unchanged.
