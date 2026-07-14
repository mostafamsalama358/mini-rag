# Implementation Plan: Answer Generation

**Branch**: `013-answer-generation` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: `specs/013-answer-generation/spec.md`

## Summary

Answer Generation is a seven-stage async pipeline that accepts a `Context` (spec 012)
and a user question, and produces an `AnswerResult` containing a cited, structured LLM
answer. Stages: prompt composition (with domain module injection), conflict-disclosure
injection, output-contract enforcement, LLM call (via `LLMProviderFactory`), citation
formatting (resolved against `Context.citation_map` by `item_id`), lightweight grounding
flag check, and no-answer short-circuit on empty context.

The module follows the established `core/{feature}/` pattern (config, errors,
interfaces, models, pipeline, registry, per-stage sub-packages) with Pydantic frozen
models, ABC interfaces, async pipeline entry point, and field-pack YAML config
resolving generic < domain < project.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: Pydantic 2.x, `core.context_builder.models.Context` (spec
012), `stores.llm.LLMProviderFactory` + `LLMInterface` (existing), PyYAML (field-pack
loading), tiktoken / char approximation (token counting, via `evidence_orchestrator`
re-use)

**Storage**: No new storage; `Context.citation_map` is the sole data source for
citation resolution; `AnswerResult` is an in-memory output contract passed to the
caller (API layer / spec 013)

**Testing**: pytest + pytest-asyncio; unit tests in `tests/unit/core/answer_generation/`;
integration test in `tests/integration/test_answer_generation_e2e.py`

**Target Platform**: Linux server (Docker); runs in the FastAPI async event loop;
LLM call may delegate to `asyncio.to_thread` for sync providers

**Project Type**: Library / pipeline stage (no HTTP surface; invoked by the answer
endpoint in the API layer)

**Performance Goals**: Pipeline overhead (all stages excluding LLM round-trip) < 200 ms
for a 4 000-token `Context` (SC-005); grounding check must add zero blocking latency
(SC-006)

**Constraints**: Must not introduce a new provider abstraction — delegates entirely to
`LLMProviderFactory`; `LLMInterface.generate_text_async` is the async call surface;
`Context` is consumed read-only, never mutated; no LLM retry on grounding flag (flag
only, never block)

**Scale/Scope**: Single-request path; no batch processing; Celery not required (sub-
second hot path); all I/O is async

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Pipeline + interfaces in `core/answer_generation/`; LLM provider wired via factory at call site; no inward imports from `stores/` | ✅ |
| G2 Feature-First | All source in `src/core/answer_generation/`; tests co-located in `tests/unit/core/answer_generation/` | ✅ |
| G3 SOLID / Plugins | `IPromptComposer`, `IOutputParser`, `ICitationFormatter`, `IGroundingChecker` are ABCs; wired via pipeline constructor; `LLMProviderFactory` used as-is | ✅ |
| G4 Async + Types | `pipeline.run()` is `async`; `LLMInterface.generate_text_async` called; full type hints on public API; Pydantic models for all I/O | ✅ |
| G5 RAG Pipeline | Citations required in `AnswerResult`; conflicts disclosed (not silently resolved); prompt versioning via `AnswerGenerationConfig`; no retrieval (upstream concern) | ✅ |
| G6 Testing | Unit tests for each stage + models; integration test with LLM mock | ✅ |
| G7 Observability | Structured logging at pipeline entry/exit with `request_id`, `plan_id`, provider name, token usage, flag count; Prometheus metrics extended | ✅ |
| G8 Security | No secrets in source; provider selected via config/env; no new SQL | ✅ |
| G9 Performance | No Celery needed (sub-second path); grounding check is in-memory | ✅ |
| G10 Stack | Python 3.13, Pydantic 2.x, pytest-asyncio; Docker deployment unchanged | ✅ |

*All gates pass. No complexity justification required.*

## Project Structure

### Documentation (this feature)

```text
specs/013-answer-generation/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   ├── AnswerResult.md
│   ├── IPromptComposer.md
│   ├── IOutputParser.md
│   ├── ICitationFormatter.md
│   └── IGroundingChecker.md
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code

```text
src/core/answer_generation/
├── __init__.py
├── config.py                      # AnswerGenerationConfig, YAML loader, resolve_answer_generation_config()
├── errors.py                      # AnswerGenerationError, SchemaVersionError, NoAnswerError, CitationResolutionError
├── interfaces.py                  # IPromptComposer, IOutputParser, ICitationFormatter, IGroundingChecker
├── models.py                      # AnswerResult, CitationReference, GroundingFlag, ComposedPrompt, CapabilityModule
├── pipeline.py                    # AnswerGenerationPipeline (7-stage orchestration)
├── registry.py                    # component registry (same pattern as context_builder/registry.py)
├── composition/
│   ├── __init__.py
│   └── default_composer.py        # DefaultPromptComposer: assembles system + user message
├── parsing/
│   ├── __init__.py
│   └── json_output_parser.py      # JsonOutputParser: parse JSON or plain-text LLM response → AnswerResult
├── citation/
│   ├── __init__.py
│   └── item_id_formatter.py       # ItemIdCitationFormatter: maps item_id markers → CitationReference
└── grounding/
    ├── __init__.py
    └── entity_tag_checker.py      # EntityTagGroundingChecker: flag entities absent from Context

src/fields/generic/answer_generation.yaml
src/fields/legal/answer_generation.yaml
src/fields/pharmacy/answer_generation.yaml

tests/unit/core/answer_generation/
├── __init__.py
├── conftest.py                    # Context/EvidencePack fixtures
├── test_models.py
├── test_composer.py
├── test_output_parser.py
├── test_citation_formatter.py
├── test_grounding_checker.py
└── test_pipeline.py

tests/integration/test_answer_generation_e2e.py
```

**Structure Decision**: Mirrors `src/core/context_builder/` exactly — one package per
pipeline stage, thin `__init__.py` re-exports, `pipeline.py` as the orchestration
entry point. No new top-level directories; no Celery tasks.

## Complexity Tracking

*No constitution violations — table omitted.*
