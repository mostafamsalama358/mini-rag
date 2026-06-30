# Implementation Plan: Pharmacy Query Enhancement

> **SUPERSEDED** — See [`002-field-registry/plan.md`](../002-field-registry/plan.md) Phase D. Do not implement.

**Branch**: `001-pharmacy-query-enhancement` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-pharmacy-query-enhancement/spec.md`

## Summary

Enhance the generic AlgoRAG platform for pharmacy use by fixing **incomplete retrieval** (the root cause of partial drug lists and missing interactions) and adding **LLM query rewriting** with pharmacy-specific intent detection. The approach combines: (1) row-aware XLSX chunking so each drug/interaction row is retrievable, (2) a `QueryUnderstandingService` that classifies intent and produces optimized search queries, (3) exhaustive retrieval mode with higher limits and disabled chunk narrowing, (4) prescription parsing for pairwise interaction checks, and (5) integration of the user-authored bilingual pharmacist prompt via `project_prompts`.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic, Celery, langchain text splitters, pandas (XLSX), existing LLM/embedding providers

**Storage**: PostgreSQL + pgvector; existing `project_prompts`, `data_chunks` (metadata JSONB extended)

**Testing**: pytest + pytest-asyncio; `tests/unit/pharmacy/`, `tests/integration/pharmacy/`

**Target Platform**: Linux server / Docker Compose (Windows dev)

**Project Type**: Web service (FastAPI backend + static SPA)

**Performance Goals**: p95 answer latency +≤2s vs baseline for query rewrite; exhaustive queries may retrieve up to 150 chunks

**Constraints**: Must remain domain-pluggable (pharmacy logic isolated in `utils/pharmacy/` + `services/QueryUnderstandingService.py`); no hard-coded provider imports in services

**Scale/Scope**: Single pharmacy project deployment; benchmark against 3 Excel source files; Arabic + English queries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Query understanding in `services/`; pharmacy patterns in `utils/pharmacy/`; wiring in `NLPController` | ☑ |
| G2 Feature-First | Co-located `tests/unit/pharmacy/`; feature docs in `specs/001-pharmacy-query-enhancement/` | ☑ |
| G3 SOLID / Plugins | Rewrite uses `generation_client` interface; no new provider coupling | ☑ |
| G4 Async + Types | `async def analyze()`; Pydantic models for `QueryIntent`, `RetrievalPlan` | ☑ |
| G5 RAG Pipeline | Hybrid retrieval preserved; reranker preserved; prompt versioning via `project_prompts`; citations added to API | ☑ |
| G6 Testing | Unit + integration tests defined in quickstart and research | ☑ |
| G7 Observability | New metrics: intent, rewrite latency, exhaustive doc count | ☑ |
| G8 Security | No secrets in code; prescription text not logged at INFO | ☑ |
| G9 Performance | Rewrite timeout 3s; pairwise cap 15; row chunking in Celery indexing | ☑ |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ☑ |

*Post-design re-check: All gates pass. No Complexity Tracking entries required.*

## Project Structure

### Documentation (this feature)

```text
specs/001-pharmacy-query-enhancement/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── query-understanding-service.md
│   └── pharmacy-answer-api.md
└── tasks.md             # Phase 2 (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
src/
├── services/
│   └── QueryUnderstandingService.py    # NEW — LLM rewrite + plan builder
├── utils/
│   └── pharmacy/                       # NEW — domain module
│       ├── __init__.py
│       ├── classifier.py               # Intent regex + pharmacy patterns
│       ├── prescription_parser.py      # Multi-drug extraction
│       ├── expansion.py                # Rule-based query expansions
│       └── models.py                   # QueryIntent, RetrievalPlan Pydantic models
├── controllers/
│   ├── NLPController.py                # MODIFY — integrate retrieval plan
│   └── ProcessController.py            # MODIFY — row-aware XLSX chunking
├── services/
│   └── RAGService.py                   # MODIFY — exhaustive mode, prompt context
├── helpers/
│   └── config.py                       # MODIFY — pharmacy settings
├── stores/llm/templates/locales/
│   ├── en/rag.py                       # MODIFY — pharmacy footer hints (fallback)
│   └── ar/rag.py                       # MODIFY — pharmacy footer hints (fallback)
└── routes/
    ├── nlp.py                          # MODIFY — citations + retrieval_meta in response
    └── schemes/nlp.py                  # MODIFY — response schema extensions

tests/
├── unit/
│   └── pharmacy/
│       ├── test_classifier.py
│       ├── test_prescription_parser.py
│       ├── test_expansion.py
│       └── test_query_understanding.py
└── integration/
    └── pharmacy/
        └── test_exhaustive_retrieval.py
```

**Structure Decision**: Single-project layout (Option 1). Pharmacy domain isolated in `utils/pharmacy/` to keep the platform generic while allowing pharmacy-specific patterns without polluting core `retrieval.py`.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

---

## Phase 0: Research (Complete)

See [research.md](./research.md). All NEEDS CLARIFICATION items resolved:

| Unknown | Resolution |
|---------|------------|
| Root cause of partial lists | Retrieval coverage + chunking + exhaustive detection gaps |
| LLM rewrite vs rules | Hybrid: rules for fast path, LLM for entity/normalization |
| XLSX strategy | Row-per-chunk behind `PHARMACY_ROW_CHUNKING` flag |
| Prompt integration | `project_prompts` with `$context` / `$question` substitution |
| Follow-up context | Entity carry-over into rewrite from chat history |

---

## Phase 1: Design (Complete)

### Data Model

See [data-model.md](./data-model.md).

### Contracts

- [query-understanding-service.md](./contracts/query-understanding-service.md)
- [pharmacy-answer-api.md](./contracts/pharmacy-answer-api.md)

### Quickstart Validation

See [quickstart.md](./quickstart.md).

### Implementation Phases (for /speckit-tasks)

#### Phase A — Foundation (P1)

1. Add `utils/pharmacy/models.py` — Pydantic models for `QueryIntent`, `PharmacyEntity`, `RetrievalPlan`
2. Add `utils/pharmacy/classifier.py` — regex intent detection (Arabic + English pharmacy patterns)
3. Add `utils/pharmacy/prescription_parser.py` — multi-drug line parser
4. Add `utils/pharmacy/expansion.py` — rule-based search term expansions (class → INN, brand → generic)
5. Add config settings in `helpers/config.py`
6. Unit tests for classifier, parser, expansion

#### Phase B — Query Understanding Service (P1)

1. Add `services/QueryUnderstandingService.py`
2. LLM rewrite prompt template in `stores/llm/templates/locales/{en,ar}/pharmacy_rewrite.py`
3. JSON schema validation + fallback to classifier
4. `build_retrieval_plan()` with exhaustive limits and target source hints
5. Unit tests with mocked generation client

#### Phase C — Retrieval Integration (P1)

1. Modify `NLPController.search_vector_db_collection` to accept optional `RetrievalPlan`
2. Multi-query execution with merge + RRF (reuse `hybrid_rrf`, `merge_retrieved_documents`)
3. Disable `focus_document_text_for_query` when `retrieval_mode=exhaustive`
4. Extend `is_exhaustive_list_query` / add `is_pharmacy_exhaustive_query` delegation
5. Wire `answer_rag_question` → analyze → plan → search → answer

#### Phase D — Row-Aware XLSX Chunking (P1)

1. Modify `ProcessController.get_file_content` / `process_file_content` for row chunks
2. Add metadata: `row_index`, `sheet_name`, `chunking_strategy`
3. Document re-index requirement in quickstart
4. Integration test: row count == chunk count for sample XLSX

#### Phase E — Prompt & Generation (P2)

1. Support `$context` / `$question` substitution in `RAGService` for `prompt_override`
2. Store user pharmacist prompt in `project_prompts` (migration seed or admin API)
3. Exhaustive generation: 8192 max tokens + completeness footer
4. Follow-up entity injection from chat history into rewrite

#### Phase F — API & Observability (P2)

1. Extend answer response with `retrieval_meta` and `citations`
2. Add Prometheus metrics
3. Integration tests for golden scenarios (muscle relaxants, Cordarone, prescription)

---

## Post-Design Constitution Re-Check

All gates remain ☑. Feature adds domain module without violating pluggable architecture. Citations added to API per §VI.4. Prompt versioning uses existing `project_prompts` per §VI.3.

---

## Key Design Decisions

1. **Retrieval before generation** — No amount of prompt engineering fixes missing context; row chunking + exhaustive mode are mandatory.
2. **LLM rewrite is additive** — Rule-based classifier ensures deterministic behavior for known patterns; LLM handles colloquial Arabic and brand/INN mapping.
3. **Generic platform preserved** — `PHARMACY_*` settings default off or auto-detect; other domains unaffected.
4. **User prompt is authoritative** — Default `rag.py` templates remain fallback; pharmacy project uses DB-stored pharmacist template.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM rewrite latency | 3s timeout + rule fallback |
| Token overflow on exhaustive lists | Char budget increase for exhaustive mode; structured bullet output |
| Re-index downtime | Celery background re-index; document in quickstart |
| Hallucinated interactions | Grounding rules in pharmacist prompt + citations required |

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Specification | `specs/001-pharmacy-query-enhancement/spec.md` | ✅ |
| Research | `specs/001-pharmacy-query-enhancement/research.md` | ✅ |
| Data Model | `specs/001-pharmacy-query-enhancement/data-model.md` | ✅ |
| Contracts | `specs/001-pharmacy-query-enhancement/contracts/` | ✅ |
| Quickstart | `specs/001-pharmacy-query-enhancement/quickstart.md` | ✅ |
| Plan | `specs/001-pharmacy-query-enhancement/plan.md` | ✅ |
| Tasks | `specs/001-pharmacy-query-enhancement/tasks.md` | ⏳ `/speckit-tasks` |

**Next step**: Run `/speckit-tasks` to generate actionable `tasks.md`, then `/speckit-implement`.
