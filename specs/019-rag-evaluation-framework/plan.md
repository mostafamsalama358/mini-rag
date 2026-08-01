# Implementation Plan: RAG Evaluation Framework

**Branch**: `enhance/query` (feature directory independent) | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/019-rag-evaluation-framework/spec.md`

**Note**: This plan designs evaluation architecture, metric ownership, governance, profiles, judges, monitoring, and validation strategy. It does **not** prescribe coding tasks, algorithms, formulas, thresholds, provider winners, or source layout. Implementation task breakdown is deferred to `/speckit-tasks` only if/when authorized separately.

## Summary

Establish a complete **production RAG evaluation architecture** that extends Feature 014’s offline golden seed into a multi-mode system: offline golden/regression, offline benchmarks, online shadow, and production monitoring — without creating a production answer/retrieval path or reassigning Feature 016 sole owners.

Approach:

1. Treat [spec.md](./spec.md) metric catalog, ownership, dependency model, profiles, judges, governance, taxonomies, and lifecycle as normative evaluation architecture.
2. Make **019** the evaluation architecture authority; preserve **014** Faithfulness / Completeness (and coverage) metric semantics; keep **018** stage diagnostics non-authoritative for release gates.
3. Bind evaluation work to reusable **Evaluation Profiles** (Smoke → Production Monitoring) rather than ad hoc suites.
4. Keep an abstract **Judge Layer** so metric identities remain stable across Rule / LLM / Human / Hybrid judges.
5. Govern datasets and benchmarks with freeze, lineage, changelog, and reproducibility rules; record rich **Evaluation Run Metadata** for comparability.
6. Standardize **Error Taxonomy**, **Drift Taxonomy**, **Experiment roles**, **Composite scores**, **Slices**, and **Alerts** as reporting/monitoring architecture — not new pipeline stages.
7. Validate via architecture-review scenarios in [quickstart.md](./quickstart.md) — not via a coding program in this plan.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated runtime for the platform; this plan itself is documentation/architecture)

**Primary Dependencies**: Existing platform stack (FastAPI, SQLAlchemy 2.x async, Pydantic, Celery) — unchanged by this plan’s scope. Evaluation architecture consumes outputs/contracts of 004/009–013 under 016 ownership and aligns with 014/018 evaluation and quality feedback concepts.

**Storage**: PostgreSQL + pgvector (unchanged). Run-store / dataset persistence strategy is non-normative here; logical Evaluation Run and Dataset entities are defined in [data-model.md](./data-model.md).

**Testing**: pytest + pytest-asyncio for any future implementation; this plan’s validation is primarily architecture-review, ownership-mapping, and governance/gate-mapping drills. Concrete suites are deferred.

**Target Platform**: Linux server / Docker Compose deployment of the existing RAG web service

**Project Type**: Evaluation architecture design for an existing RAG web service (not a new user-facing product surface)

**Performance Goals**: Out of scope as a latency program. Latency and Cost are first-class *evaluation metrics* and monitoring signals (spec §2 / §8), not implementation SLOs defined here.

**Constraints**:
- Architecture-only: no algorithms, formulas, concrete thresholds, code, pseudocode, class diagrams, ADRs, or sprint tasks in this feature’s plan artifacts
- Sole-owner and M0 freeze (016) binding — no second retrieval or answer path; evaluation is offline/CI/shadow/monitoring only
- Frozen external answer API (015) — evaluation may consume dual-run/shadow outputs; MUST NOT redefine external fields
- 014 metric semantics for Faithfulness/Completeness preserved; 019 owns evaluation architecture authority
- 018 stage metrics remain diagnostic; on release disagreement, 019 gates win
- Judge implementations out of scope; only interchangeability contract is normative
- Physical package/layout non-normative

**Scale/Scope**: Full evaluation ecosystem — datasets/benchmarks, metric ownership & dependencies, judges & confidence, profiles & gates, experiment roles, composites, slices, error/drift/alert taxonomies, run metadata, lifecycle, future extension points; compatibility with 014–018

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in application/core; infra behind interfaces; no inward imports | ✅ Evaluation contracts/interfaces vs persistence/telemetry adapters; no inward infra coupling introduced |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ Spec/plan under `specs/019-…`; cross-cutting eval justified in Complexity Tracking |
| G3 SOLID / Plugins | Externals via interfaces; Composition wires | ✅ Judge Layer is interchangeable behind stable metric contracts; no provider lock-in |
| G4 Async + Types | Async I/O; typed public APIs | ✅ Unchanged platform norms; eval remains async-friendly and non-request-path |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations | ✅ Citation Accuracy / grounding metrics reinforce citation obligations; prompt/version fingerprints on runs |
| G6 Testing | Unit/integration planned for changed behavior | ✅ Architecture validation gates in quickstart; concrete test authorship deferred to tasks |
| G7 Observability | Structured logging + metrics at boundaries | ✅ Run metadata, monitoring views, drift/alerts, Quality Trace reuse are first-class |
| G8 Security | No secrets in artifacts | ✅ Core Golden CI must not require secrets/PII; no auth redesign |
| G9 Performance | Long work in Celery; no unjustified sync work | ✅ Evaluation never mandatory on user request path; online modes asynchronous |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ No stack change |

## Project Structure

### Documentation (this feature)

```text
specs/019-rag-evaluation-framework/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1 — evaluation architecture entities
├── quickstart.md           # Phase 1 — architecture validation guide
├── contracts/              # Phase 1 — normative contracts
│   ├── metric-system.md
│   ├── judge-layer.md
│   ├── dataset-benchmark-governance.md
│   ├── evaluation-pipeline.md
│   ├── experiment-comparison.md
│   ├── observability-monitoring.md
│   └── compatibility.md
├── spec.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

This plan does **not** redefine source layout. Physical packages remain non-normative. Future implementation may map logical evaluation contracts to modules after `/speckit-tasks` authorization — not in this plan.

```text
src/                     # existing platform (layout non-normative for this plan)
tests/                   # existing test tree; future gates may extend 014 suites
specs/004…018/           # related Spec Kit features
.specify/memory/         # constitution
```

**Structure Decision**: Documentation-only deliverables for Phase 0–1. No new source tree is introduced by planning.

## Architecture Design

### Design stance

| Prescribe | Do not prescribe |
|-----------|------------------|
| Metric ownership, dependency, honesty rules | Formulas, numeric thresholds |
| Evaluation profiles and gate classes | CI vendor, job YAML, schedules |
| Dataset/benchmark governance & lifecycle | Storage format, authoring UI |
| Judge Layer interchangeability | Judge prompts, models, heuristics |
| Experiment roles & composite purpose | Deployment/canary traffic mechanics |
| Error / drift / alert taxonomies | Dashboard product or alert routing tooling |
| Evaluation Run Metadata fields | Persistence schema or wire encoding |
| Compatibility with 014–018 | New production stages or ownership reassignment |

### Evaluation lifecycle (normative summary)

See [spec.md](./spec.md) Evaluation Lifecycle:

`Dataset → Evaluation → Reports → Regression Gates → Release → Shadow → Production Monitoring → Dataset Evolution`

### Ownership map (normative — no reassignment)

| Concern | Production owner (016) | Evaluation role |
|---------|------------------------|-----------------|
| Query Understanding | `query_understanding` | Label/subject when present |
| Retrieval Planner | `retrieval_planning` | Primary owner: Plan Fidelity, Strategy Alignment |
| Retrieval Engine | `retrieval_execution` | Primary owner: Recall, Precision, MRR, NDCG |
| Evidence Orchestrator | evidence owner | Supporting for completeness/faithfulness diagnostics |
| Context Builder | context owner | Supporting for citation chain |
| Answer Generation | answer owner | Primary owner: Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate |
| Whole Pipeline (ops attribution) | *not a new 016 owner* | Evaluation attribution sink for Latency, Cost |
| Evaluation system | *non-production path* | Orchestration, judges, gates, reports, monitoring contracts |

### Compatibility summary

| Feature | Stance |
|---------|--------|
| 014 | Semantic seed for Faithfulness/Completeness/coverage; subsumed into 019 architecture authority |
| 015 | Shadow/dual-run/canary inputs allowed; no second answer owner |
| 016 | Sole-owner + M0 freeze binding; eval not a production stage |
| 018 | Stage diagnostics feed eval; 019 gates win on release disagreement |
| 017 | Orthogonal ingest reliability |

Details: [contracts/compatibility.md](./contracts/compatibility.md)

## Validation Strategy

Architecture validation (not implementation verification) is defined in [quickstart.md](./quickstart.md):

1. Ownership & sole-path drills (no new production stage)
2. Metric Ownership / dependency attribution drill
3. Profile → gate mapping drill
4. Dataset/benchmark freeze & reproducibility drill
5. Judge stability drill (metric identity unchanged across judge types)
6. Experiment role & champion/challenger comparability drill
7. Drift/alert vs offline gate authority drill
8. Compatibility sweep across 014–018

Success criteria references: SC-001–SC-014 in [spec.md](./spec.md).

## Complexity Tracking

| Complexity | Why needed | Simpler alternative rejected |
|------------|------------|------------------------------|
| Multi-mode evaluation (offline/online/monitor) | Production RAG needs merge gates *and* live drift | Offline-only (014) — insufficient for drift/ops |
| Metric Ownership + Dependency Model | Prevents unattributable multi-metric failures | Single “quality score” only — hides root cause |
| Judge Layer abstraction | Future multi-judge without metric churn | Hard-wire one scorer type — brittle |
| Dataset + Benchmark governance | Release claims require freeze/lineage | Ad hoc fixture folders — non-reproducible |
| Profiles instead of one suite | Different assurance levels (Smoke→Release) | One mega-suite always — too slow/noisy for PR |

## Post-Design Constitution Re-Check

*Completed after Phase 1 artifacts.*

| Gate | Post-design status |
|------|--------------------|
| G1–G5 | ✅ Contracts keep evaluation outside production stages; citation/version fingerprints retained |
| G6 | ✅ Quickstart architecture drills; implementation tests deferred |
| G7 | ✅ Observability contract defines views, drift, alerts, run metadata |
| G8–G10 | ✅ No secrets, no request-path eval, no stack change |

**Gate result**: PASS — proceed; unresolved clarifications: none (see [research.md](./research.md)).
)
