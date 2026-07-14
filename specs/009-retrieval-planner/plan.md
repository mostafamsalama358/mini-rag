# Implementation Plan: Retrieval Planner

**Branch**: `009-retrieval-planner` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-retrieval-planner/spec.md`

---

## Summary

Introduce a **Retrieval Planner** — a stateless, deterministic, CPU-bound pipeline stage
that converts a natural-language query (via the `ParseResult` produced by spec 004) into
an immutable **`RetrievalPlan`**: the stable public contract consumed by Retrieval Engine V2
(spec 010) and all downstream specs (011–013).

The Planner performs pure reasoning across six pluggable sub-components:
`IIntentClassifier`, `IEntityResolver`, `IFilterExtractor`, `IClarificationDetector`,
`IStrategySelector`, and a `BudgetEstimator`. Default implementations are
fully deterministic and rule-based — no LLM inference, no vector search, no I/O. The
Planner is domain-agnostic; all domain behaviour is driven by field pack YAML (spec 002).

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: Pydantic v2 (models + validation); `core.query_parser.schema.ParseResult` (input); field pack YAML via `core.field_resolution` (spec 002)

**Storage**: None — the Planner is a stateless in-memory transform; it neither reads from nor writes to any data store

**Testing**: pytest; `tests/unit/core/retrieval_planner/` (per-stage unit tests) + `tests/integration/test_retrieval_planner_golden.py` (golden plan suite)

**Target Platform**: Linux server, Docker (same as existing platform)

**Project Type**: Internal RAG platform pipeline module (inline, synchronous, request-path)

**Performance Goals**: Planning latency ≤ 50 ms for standard queries (SC-002); all pipeline stages are O(k) where k = number of entities/filters (small, < 20 typically)

**Constraints**:
- Zero retrieval operations — no vector search, no index lookup, no database query (FR-016, SC-006)
- `RetrievalPlan` must be immutable once produced — `ConfigDict(frozen=True)` on all published models
- Stateless between requests — no instance-level mutable state (NFR-004)
- `StrategyType` must be open/extensible — not a closed `Literal` enum (FR-014)
- `RetrievalPlan` must contain no retrieval-engine-specific artifacts (FR-017)

**Scale/Scope**: One `RetrievalPlan` per user query, in the request path; per-request invocation via `RAGService` (eventually); no Celery needed (< 50 ms inline)

---

## Constitution Check

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|---|---|---|
| G1 Clean Architecture | Planner domain models + interfaces in `src/core/retrieval_planner/`; no inward imports from retrieval infrastructure | ✅ |
| G2 Feature-First | All planner code co-located in `src/core/retrieval_planner/`; tests co-located in `tests/unit/core/retrieval_planner/` | ✅ |
| G3 SOLID / Plugins | Five pluggable interfaces (`IIntentClassifier`, `IEntityResolver`, `IFilterExtractor`, `IStrategySelector`, `IClarificationDetector`); default implementations wired via `RetrievalPlannerRegistry`; Open/Closed for new strategies | ✅ |
| G4 Async + Types | Planner core is sync (CPU-bound, < 50 ms); async wrapper added at service boundary; all public APIs fully type-hinted; Pydantic v2 models throughout | ✅ |
| G5 RAG Pipeline | Pre-retrieval stage; `citation_required` in `RetrievalConstraints` propagates the citation requirement (Constitution VI.4) to downstream retrieval and answer generation | ✅ |
| G6 Testing | Unit tests per pipeline stage (7 test modules); golden plan integration test suite asserting full plan shape stability | ✅ |
| G7 Observability | Structured logging at planner boundary: `query_id`, `intent_category`, `strategies`, `planner_confidence`, `latency_ms` (NFR-011) | ✅ |
| G8 Security | No new secrets; no SQL; query text sanitised upstream by query parser (spec 004); planner receives canonical_query only | ✅ |
| G9 Performance | Planner runs inline (< 50 ms); Celery not needed for this stage; no long-running work | ✅ |
| G10 Stack | Python 3.13, Pydantic v2, no deviations from mandated stack | ✅ |

*All gates pass. No complexity justification required.*

---

## Project Structure

### Documentation (this feature)

```text
specs/009-retrieval-planner/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   └── pipeline-contract.md
└── tasks.md             ← Phase 2 output (/speckit-tasks — not created here)
```

### Source Code

```text
src/core/retrieval_planner/
├── __init__.py
├── models.py                  # StrategyType, IntentCategory, QueryIntent,
│                              # ResolvedEntity, QueryFilter, RetrievalLimits,
│                              # RetrievalConstraints, ExecutionHints, OutputShape,
│                              # PlannerDiagnostics, RetrievalPlanMetadata,
│                              # RetrievalPlan, RetrievalPlannerConfig
├── interfaces.py              # IRetrievalPlanner, IIntentClassifier, IEntityResolver,
│                              # IFilterExtractor, IStrategySelector,
│                              # IClarificationDetector
├── pipeline.py                # RetrievalPlannerPipeline (orchestrator)
├── assembly.py                # PlanAssembler
├── registry.py                # RetrievalPlannerRegistry (maps strategy ids → implementations)
├── errors.py                  # RetrievalPlannerError, PlannerConfigError,
│                              # StrategyNotFoundError, PlanAssemblyError
├── intent/
│   ├── __init__.py
│   └── rule_based.py          # RuleBasedIntentClassifier (default)
├── entities/
│   ├── __init__.py
│   └── query_plan_resolver.py # QueryPlanEntityResolver (default)
├── filters/
│   ├── __init__.py
│   └── query_plan_extractor.py # QueryPlanFilterExtractor (default)
├── strategies/
│   ├── __init__.py
│   └── config_driven.py       # ConfigDrivenStrategySelector (default)
├── clarification/
│   ├── __init__.py
│   └── confidence_based.py    # ConfidenceBasedClarificationDetector (default)
└── limits/
    ├── __init__.py
    └── budget_estimator.py    # BudgetEstimator (default)

src/fields/generic/retrieval_planning.yaml  # Generic field pack: strategy mappings,
                                            # budget defaults, confidence thresholds,
                                            # entity types, intent→strategy table

tests/unit/core/retrieval_planner/
├── __init__.py
├── conftest.py                # Shared ParseResult fixtures (clear, ambiguous, tabular,
│                              # keyword, empty, multi-intent)
├── test_models.py             # Immutability, ID stability, StrategyType open type
├── test_intent_classifier.py  # RuleBasedIntentClassifier coverage
├── test_entity_resolver.py    # QueryPlanEntityResolver
├── test_filter_extractor.py   # QueryPlanFilterExtractor
├── test_strategy_selector.py  # ConfigDrivenStrategySelector
├── test_clarification_detector.py  # ConfidenceBasedClarificationDetector
└── test_plan_assembler.py     # PlanAssembler + full pipeline integration

tests/integration/
└── test_retrieval_planner_golden.py  # Golden plan suite: 15+ labelled queries,
                                      # asserting full plan shape + primary strategy
```

---

## Complexity Tracking

No Constitution Check violations. No complexity justifications required.
