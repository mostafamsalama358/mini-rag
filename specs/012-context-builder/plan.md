# Implementation Plan: Context Builder

**Branch**: `012-context-builder` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

## Summary

Context Builder is a six-stage async pipeline that consumes an `EvidencePack` (spec 011,
schema v1.0.0) and emits a token-budget-compliant `Context` object for Answer Generation
(spec 013). The pipeline runs in order: allocate budget → select under budget →
compress high-compressibility items → detect conflicts → stitch by document structure →
final-pass dedup → assemble. All external behaviour is injected through four pluggable
interfaces; a heuristic truncation compressor is the default to keep the hot path free
of LLM calls. The implementation mirrors the `evidence_orchestrator` package structure
already present at `src/core/evidence_orchestrator/`.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Pydantic v2 (models + config validation), `core.evidence_orchestrator`
(imports `EvidencePack`, `EvidenceItem`, `Citation`, `ITokenCounter`,
`CharacterApproximationTokenCounter`, `char_ngrams`, `jaccard_similarity`)

**Storage**: None — Context Builder is a stateless in-process pipeline; no DB access.

**Testing**: pytest + pytest-asyncio; unit tests at `tests/unit/core/context_builder/`;
integration test at `tests/integration/test_context_builder_e2e.py`

**Target Platform**: Linux server (same Docker environment as the rest of the RAG system)

**Project Type**: Internal library / pipeline component within the `src/core/` layer

**Performance Goals**: Full pipeline (excluding optional LLM compression) ≤ 150 ms p95
on a 50-item `EvidencePack` (SC-005)

**Constraints**: No LLM call on the hot path by default; heuristic compressor is the
default implementation. LLM compressor is an optional pluggable implementation.
`ITokenCounter` reused from spec 011 — not duplicated.

**Scale/Scope**: Typical input: 10–100 `EvidenceItem` objects. Celery offload not
required for this stage (sub-150 ms synchronous; offload is Evidence Orchestrator's
concern for large retrieval sets).

## Constitution Check

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Domain models in `models.py`; pipeline orchestration in `pipeline.py`; concrete implementations in sub-packages; no inward imports | ✅ |
| G2 Feature-First | All code under `src/core/context_builder/`; all tests under `tests/unit/core/context_builder/` and `tests/integration/` | ✅ |
| G3 SOLID / Plugins | Four interfaces (`ITokenBudgetAllocator`, `IContextCompressor`, `IConflictDetector`, `IContextStitcher`); concrete impls wired via `ContextBuilderRegistry` | ✅ |
| G4 Async + Types | All pipeline stages `async`; public APIs fully typed; `Context`, `ContextBlock`, `ConflictGroup`, `ContextMetadata`, `ContextBuilderConfig` backed by Pydantic | ✅ |
| G5 RAG Pipeline | Citation map 1:1 preserved (FR-008); no prompt construction (FR-011); citations are the responsibility of this component — fully preserved | ✅ |
| G6 Testing | Unit tests for each stage + integration e2e test planned (NFR-006) | ✅ |
| G7 Observability | Structured log entry per stage with `plan_id`, `pack_id`, `items_in`, `items_out`, `token_budget`, stage latency; `CONTEXT_HARD_DROP` event (NFR-007) | ✅ |
| G8 Security | No secrets; no SQL; no file I/O at runtime | ✅ |
| G9 Performance | Hot path is pure Python + Pydantic; no blocking I/O; LLM compressor optional | ✅ |
| G10 Stack | Python 3.13, Pydantic v2, pytest, Docker; no new top-level dependencies | ✅ |

All gates pass. No complexity tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/012-context-builder/
├── plan.md              ← this file
├── research.md          ← Phase 0
├── data-model.md        ← Phase 1
├── quickstart.md        ← Phase 1
├── contracts/
│   ├── Context.md
│   ├── ITokenBudgetAllocator.md
│   ├── IContextCompressor.md
│   ├── IConflictDetector.md
│   └── IContextStitcher.md
└── tasks.md             ← Phase 2 (/speckit-tasks — not yet created)
```

### Source Code

```text
src/core/context_builder/
├── __init__.py
├── config.py                         # ContextBuilderConfig (Pydantic)
├── errors.py                         # EvidencePackVersionError, ContextBuildError, etc.
├── interfaces.py                     # ITokenBudgetAllocator, IContextCompressor,
│                                     # IConflictDetector, IContextStitcher
├── models.py                         # Context, ContextBlock, ConflictGroup, ContextMetadata
├── pipeline.py                       # ContextBuilderPipeline (async orchestration)
├── registry.py                       # ContextBuilderRegistry (factory / wiring)
├── budget/
│   ├── __init__.py
│   └── default_allocator.py          # DefaultTokenBudgetAllocator
├── compression/
│   ├── __init__.py
│   └── heuristic_compressor.py       # HeuristicTruncationCompressor (default)
├── conflict/
│   ├── __init__.py
│   └── entity_tag_detector.py        # EntityTagConflictDetector
├── dedup/
│   ├── __init__.py
│   └── text_similarity_dedup.py      # FinalPassDeduplicator (char n-gram Jaccard)
└── stitching/
    ├── __init__.py
    └── section_path_stitcher.py      # SectionPathStitcher

src/fields/generic/context_builder.yaml
src/fields/pharmacy/context_builder.yaml
src/fields/legal/context_builder.yaml

tests/unit/core/context_builder/
├── __init__.py
├── conftest.py
├── test_models.py
├── test_budget_allocator.py
├── test_selector.py
├── test_heuristic_compressor.py
├── test_conflict_detector.py
├── test_stitcher.py
├── test_final_dedup.py
└── test_pipeline.py

tests/integration/
└── test_context_builder_e2e.py
```

**Structure Decision**: Mirrors `src/core/evidence_orchestrator/` exactly — one sub-package
per pipeline stage, a flat `interfaces.py`, `models.py`, `config.py`, `errors.py`,
`pipeline.py`, and `registry.py` at the package root. This pattern is already established
and understood by the team.

## Complexity Tracking

No constitution violations — no entries required.
