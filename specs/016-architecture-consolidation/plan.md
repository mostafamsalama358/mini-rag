# Implementation Plan: Architecture Consolidation

**Branch**: `016-architecture-consolidation` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-architecture-consolidation/spec.md`

**Note**: This plan designs governance, contracts, and migration strategy. It does **not** prescribe coding tasks, package winners, or source layout. Implementation task breakdown is deferred to `/speckit-tasks` only if/when authorized separately.

**Setup note**: `.specify/scripts/powershell/setup-plan.ps1 -Json` could not be executed in this environment (shell allowlist). Paths resolved from `.specify/feature.json` and the plan template.

## Summary

Consolidate parallel production paths, duplicated ownership, and lifecycle drift into a **governance-first architecture**: one production path per capability, one owner per concern, one canonical contract per shared concept, inward-only dependencies, and Composition as the sole wiring authority.

Approach:

1. Treat [spec.md](./spec.md) Principles, Invariants, Anti-Patterns, and Governance as normative.
2. Use Owner Selection Criteria (not history/layout) when establishing Active Production Owners.
3. Sequence cutover before retirement (M0–M8), with Answer before Search (ADR-002).
4. Keep external answer contract frozen (ADR-003); keep knowledge off the active path until a consumer exists (ADR-004).
5. Validate via Architecture / Code / Runtime / Operational gates — not via a component catalog in this plan.

Depends on answer-path cutover vehicle from `015-unified-pipeline-migration` as an assumed external mechanism (spec Assumptions); this plan does not redesign that cutover product.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated runtime for the platform; this plan itself is documentation/governance)

**Primary Dependencies**: Existing platform stack (FastAPI, SQLAlchemy 2.x async, Pydantic, Celery) — unchanged by this plan’s scope. Consolidation reuses current composition and offline evaluation gates.

**Storage**: PostgreSQL + pgvector (unchanged). Re-index is a compatibility event when sole chunking/embed-text policy changes — not a storage redesign.

**Testing**: pytest + pytest-asyncio; architecture validation is primarily review/gate based; runtime/regression gates reuse existing answer quality / golden mechanisms where applicable

**Target Platform**: Linux server / Docker Compose deployment of the existing web service

**Project Type**: Architecture governance + migration strategy for an existing RAG web service (not a new product surface)

**Performance Goals**: Out of scope (spec Out of Scope). No new latency targets introduced by consolidation.

**Constraints**:
- Implementation-independent: logical concerns/contracts/ownership only
- Frozen external answer contract during consolidation
- No parallel production paths after sole-owner declaration
- No implementation task lists in this plan
- Physical layout and concrete type names are non-normative

**Scale/Scope**: Four capabilities (Answer, Ingest, Search, Offline Evaluation); migration phases M0–M8; governance baseline for all future features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in application/core; infra behind interfaces; no inward imports | ✅ Strengthens via P5–P7, I4, I8, AP4/AP6 |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ Spec/plan under `specs/016-…`; cross-cutting nature justified below |
| G3 SOLID / Plugins | Externals via interfaces; Composition wires | ✅ P6/P7; Owner Selection prefers extensibility |
| G4 Async + Types | Async I/O; typed public APIs | ✅ Unchanged platform norms; not redesigned here |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ Retained as properties of canonical Answer capability (NFR-003) |
| G6 Testing | Unit/integration planned for changed behavior | ✅ Validation categories define gates; tasks deferred |
| G7 Observability | Structured logging + path/owner observability until sole-path | ✅ Spec Operational Validation |
| G8 Security | No secrets in artifacts; no auth redesign in scope | ✅ Out of Scope excludes unrelated security programs |
| G9 Performance | Long work in Celery; no perf program here | ✅ Perf optimization Out of Scope |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ No stack change |

## Project Structure

### Documentation (this feature)

```text
specs/016-architecture-consolidation/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1 — governance entities
├── quickstart.md        # Phase 1 — validation guide
├── contracts/           # Phase 1 — normative contracts
│   ├── governance.md
│   ├── dependency-boundaries.md
│   ├── lifecycle.md
│   └── api-stability.md
├── spec.md              # Architecture specification
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

This plan does **not** redefine source layout. Physical packages remain non-normative (spec D6 / P9 / AP14). Future implementation docs may map logical Owners to modules; that mapping is **not** part of this architecture plan.

```text
src/                     # existing platform (layout non-normative for this plan)
tests/                   # existing test tree; gates may reuse suites
specs/                   # Spec Kit features including 015 (cutover vehicle) and 016 (this plan)
.specify/memory/         # constitution (external governance authority)
```

**Structure Decision**: Documentation-only deliverables for Phase 0–1. No new source tree is introduced by planning. Any later mapping of Owners → modules belongs in implementation documentation after Owner Selection Criteria are applied — not in this plan.

## Architecture Design

### Design stance

| Prescribe | Do not prescribe |
|-----------|------------------|
| Principles, invariants, anti-patterns | Fixed stage orchestration order (unless ADR/invariant) |
| Capability cards (concerns/contracts/deps) | Package/folder winners |
| Ownership rules + selection criteria | Full component catalog |
| Lifecycle vocabulary + convergence | Coding steps / file edits |
| Migration phase outcomes + gates | Algorithm or quality tuning |

### Capability model (normative summary)

See [spec.md](./spec.md) Canonical Architecture. Each capability defines Purpose, Required Concerns, Required Contracts, Ownership, Allowed Dependencies, Forbidden Dependencies.

### Owner selection (normative process)

When a concern has competing implementations:

1. Score candidates against Owner Selection Criteria (alignment, maturity, stability, validation, extensibility, maintainability).
2. Forbid selection by age, folder, historical ownership, or convenience alone.
3. Declare Active Production Owner; classify others Consolidate / Retire After Cutover / non-production lifecycle.
4. Record contested selections as ADRs when multiple valid alternatives existed.

### Relationship to 015

| Topic | Owner of decision |
|-------|-------------------|
| Answer dual-run → sole-path mechanism | 015 (assumed cutover vehicle) |
| Target architecture & governance after cutover | 016 (this plan) |
| Frozen answer API | 015 contract + 016 ADR-003 / [contracts/api-stability.md](./contracts/api-stability.md) |
| Search consolidation timing | 016 ADR-002 |
| Knowledge activation | 016 ADR-004 |

### Migration phases (outcomes only)

| Phase | Outcome | Primary gate category |
|-------|---------|----------------------|
| M0 | Dual-path growth frozen | Architecture / Process |
| M1 | Answer sole user-visible path | Runtime + Operational |
| M2 | Retrieval sole owner for Answer; Search interim explicit | Architecture + Runtime |
| M3 | One production contract per shared concept | Architecture + Code |
| M4 | Ingest/chunking sole ownership model | Runtime + Code |
| M5 | Core free of concrete infra deps | Code + Architecture |
| M6 | Domain heuristics owned by Domain Packs | Architecture + Code |
| M7 | Retire competitors + transitional diagnostics | Code + Operational |
| M8 | Lifecycle honesty for inactive capabilities | Architecture + Process |

Detailed phase mechanics for answer cutover remain in 015; 016 defines exit meaning in governance terms.

## Validation Strategy

Aligned with spec Validation categories. Runnable checks are listed in [quickstart.md](./quickstart.md).

| Category | Proves |
|----------|--------|
| Architecture | Capability cards complete; one owner; no anti-patterns; ADR/Principle traceability |
| Code | Deterministic wiring; no core→concrete infra; no hidden paths; contract uniqueness |
| Runtime | Cutover quality tolerance; ingest critical formats; diagnostics not user-visible |
| Operational | Observability, soak, rollback, docs=lifecycle truth, re-index waiver policy |

## Complexity Tracking

| Violation / Tension | Why Needed | Simpler Alternative Rejected Because |
|---------------------|------------|--------------------------------------|
| Cross-cutting governance (vs narrow feature slice) | Drift is systemic across Answer/Ingest/Search | Per-module cleanup without governance recreates parallel paths |
| Deferred physical owner mapping | Spec forbids layout-coupled winners | Naming package survivors now violates AP12/AP14 and Owner Selection Criteria |
| Dependence on 015 cutover vehicle | Avoid reinventing dual-run product | Redesigning cutover inside 016 expands Out of Scope into implementation program |

## Post-Design Constitution Re-Check

| Gate | Post-design | Notes |
|------|-------------|-------|
| G1–G5, G7–G10 | ✅ | Design reinforces constitution; no unjustified stack/perf/security expansion |
| G6 | ✅ | Gates defined; concrete test authorship deferred to tasks (out of this command) |
| G2 | ✅ with justification | Cross-cutting architecture feature; scoped under `specs/016-…` with co-located artifacts |
