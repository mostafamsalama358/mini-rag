# Implementation Plan: Answer Quality

**Branch**: `014-answer-quality` | **Date**: 2026-07-15 | **Spec**: [spec.md](spec.md)

## Summary

Build an offline evaluation and gating layer that measures quality of the full
AlgoRAG pipeline (006–013) by running a golden test suite against recorded pipeline
outputs. The layer exposes four pluggable interfaces (`IGoldenTestRunner`,
`ICoverageEvaluator`, `IFaithfulnessScorer`, `ICompletenessScorer`) and persists
`EvaluationResult` records for regression tracking. It consumes `AnswerResult`
(spec 013), `Context` (spec 012), and `EvidencePack` (spec 011) as read-only inputs;
it does not modify any pipeline stage.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: Pydantic (models and config), PyYAML (fixture loading),
pytest + pytest-asyncio (test harness integration), standard library `re` and
`pathlib` (text matching and file I/O)

**Storage**: Local JSON files in a configurable run-store directory (v1); no DB
required for the evaluation layer itself

**Testing**: pytest + pytest-asyncio; unit tests in `tests/unit/core/answer_quality/`;
integration golden test in `tests/integration/test_answer_quality_golden.py`

**Target Platform**: Linux server (CI) and local developer machine

**Project Type**: Evaluation framework / quality gate library (offline, not
user-facing)

**Performance Goals**: Full golden suite (≥10 questions) evaluated against
pre-recorded pipeline outputs in ≤60 seconds (SC-001)

**Constraints**: Read-only access to pipeline outputs; no live LLM or embedding
calls in core scoring logic; no mutation of `AnswerResult`, `Context`, or
`EvidencePack`

**Scale/Scope**: 10–100 golden questions per fixture set; one evaluation run per
CI commit

## Constitution Check

*GATE: Must pass before Phase 1 design. Re-checked after Phase 1.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? | Notes |
|------|-------------|-------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ✅ | Interfaces in `answer_quality/interfaces.py`; concrete scorers in sub-modules; persistence in `regression/`; no inward imports from infrastructure |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ | All source under `src/core/answer_quality/`; all tests under `tests/unit/core/answer_quality/` and `tests/integration/` |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ✅ | `ICoverageEvaluator`, `IFaithfulnessScorer`, `ICompletenessScorer`, `IRegressionStore` are abstract; concrete implementations registered via `AnswerQualityRegistry` |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic schemas | ✅ | All scorer and runner methods `async`; all data models Pydantic; full type hints |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ | N/A — evaluation layer; no retrieval or generation happens here; see Complexity Tracking |
| G6 Testing | Unit and integration tests planned for changed behavior | ✅ | Unit: one pass + one fail test per dimension; integration: full golden suite against recorded snapshot |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ | Structured logs per run (`run_id`, `question_id`, dimension scores, `passed`) |
| G8 Security | No secrets in code; input validation; parameterized SQL | ✅ | No secrets; no SQL; fixture files local YAML; no external API calls by default |
| G9 Performance | Long work in Celery; batching/pooling considered | ✅ | Offline/CLI invocation only; no HTTP handler; Celery not applicable — see Complexity Tracking |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ | Python 3.13; FastAPI/SQLAlchemy/Celery/Docker not needed for the offline evaluation module |

## Project Structure

### Documentation (this feature)

```text
specs/014-answer-quality/
├── plan.md          ← this file
├── research.md      ← Phase 0 output
├── data-model.md    ← Phase 1 output
├── quickstart.md    ← Phase 1 output
├── contracts/       ← Phase 1 output
│   ├── interfaces.md
│   └── schemas.md
└── tasks.md         ← Phase 2 output (produced by /speckit-tasks)
```

### Source Code (repository root)

```text
src/core/answer_quality/
├── __init__.py
├── config.py                  # AnswerQualityConfig (thresholds, paths)
├── errors.py                  # EvaluationError, FixtureLoadError, etc.
├── interfaces.py              # IGoldenTestRunner, ICoverageEvaluator,
│                              # IFaithfulnessScorer, ICompletenessScorer,
│                              # IRegressionStore
├── models.py                  # GoldenTestFixture, GoldenTestResult,
│                              # EvaluationResult, CoverageResult,
│                              # FaithfulnessResult, CompletenessResult,
│                              # RegressionDiff, ScoreThresholds
├── pipeline.py                # GoldenTestRunner (orchestrates full evaluation)
├── registry.py                # AnswerQualityRegistry (factory / DI wiring)
├── coverage/
│   ├── __init__.py
│   └── evaluator.py           # DocIdCoverageEvaluator implements ICoverageEvaluator
├── faithfulness/
│   ├── __init__.py
│   └── scorer.py              # TextFaithfulnessScorer implements IFaithfulnessScorer
├── completeness/
│   ├── __init__.py
│   └── scorer.py              # KeywordCompletenessScorer implements ICompletenessScorer
└── regression/
    ├── __init__.py
    └── store.py               # JsonRegressionStore implements IRegressionStore

tests/unit/core/answer_quality/
├── __init__.py
├── test_coverage_evaluator.py
├── test_faithfulness_scorer.py
├── test_completeness_scorer.py
├── test_models.py
└── test_pipeline.py

tests/integration/
└── test_answer_quality_golden.py

tests/fixtures/answer_quality/
└── generic_golden.yaml        # sample golden fixture set (domain-agnostic)
```

**Structure Decision**: Single-project layout matching `src/core/answer_generation/`
and `src/core/context_builder/` conventions. Each pluggable scoring concern gets its
own sub-package (coverage, faithfulness, completeness, regression) so implementations
can be swapped without touching sibling packages.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| G5 RAG Pipeline — not applicable | Answer quality is a pure evaluation layer; it does not perform retrieval, reranking, or generation | Applying RAG pipeline rules to an offline scorer would add irrelevant constraints (e.g. requiring hybrid retrieval in a test harness) |
| G9 Celery — not used | Evaluation runs from CLI or CI, not from an HTTP request handler; there is no HTTP timeout budget to protect | Running a 60-second golden suite in a Celery task would add queue/broker dependency to the CI workflow with no benefit |
