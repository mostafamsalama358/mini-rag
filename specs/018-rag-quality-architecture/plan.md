# Implementation Plan: RAG Quality Architecture

**Branch**: `enhance/query` (feature directory independent) | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-rag-quality-architecture/spec.md`

**Note**: This plan designs quality contracts, continuity rules, and validation strategy. It does **not** prescribe coding tasks, algorithms, provider winners, or source layout. Implementation task breakdown is deferred to `/speckit-tasks` only if/when authorized separately.

## Summary

Strengthen end-to-end **retrieval quality, evidence quality, grounding quality, and final answer quality** by extending stage contracts and cross-stage continuity — without merging stages, adding parallel pipelines, or reassigning Feature 016 sole owners.

Approach:

1. Treat [spec.md](./spec.md) §§1–20 and Contracts C1–C12 as normative architecture.
2. Make Query Understanding → Planner a hard handoff (no re-parse); Planner owns strategy architecture; Engine owns candidate lifecycle including score calibration.
3. Keep coverage validation and missing-evidence states under Evidence; Context owns priority/compression; Answer owns claim-level verification and no-answer decisions.
4. Accumulate **Quality Context** and append-only **Quality Trace** without replacing stage outputs.
5. Keep Feature 014 as offline evaluation authority and configuration feedback source; keep 015 dual-run transitional; keep 017 ingest orthogonal.
6. Validate via architecture review scenarios in [quickstart.md](./quickstart.md) — not via a coding program in this plan.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated runtime for the platform; this plan itself is documentation/architecture)

**Primary Dependencies**: Existing platform stack (FastAPI, SQLAlchemy 2.x async, Pydantic, Celery) — unchanged by this plan’s scope. Quality architecture extends contracts of 004/009–014 under 016 ownership.

**Storage**: PostgreSQL + pgvector (unchanged). No storage redesign. Quality Trace / Quality Context are logical accompanying artifacts; persistence strategy is non-normative here.

**Testing**: pytest + pytest-asyncio for any future implementation; this plan’s validation is primarily architecture-review and continuity-mapping gates. Offline regression remains Feature 014.

**Target Platform**: Linux server / Docker Compose deployment of the existing RAG web service

**Project Type**: Architecture quality design for an existing RAG web service (not a new product surface)

**Performance Goals**: Out of scope for this architecture plan. Token efficiency is a quality continuity concern (Contract C6), not a latency program.

**Constraints**:
- Architecture-only: no algorithms, code, pseudocode, class diagrams, ADRs, or sprint tasks in this feature’s plan artifacts
- Sole-owner and M0 freeze (016) binding — no second retrieval or answer path
- Frozen external answer API (015) — internal Quality Context/Trace may exceed external fields
- Feature 014 metrics not redefined; feedback stays offline
- Feature 017 ingest reliability remains orthogonal
- Physical package/layout non-normative

**Scale/Scope**: Quality contracts across Query Understanding → Planner → Engine → Evidence → Context → Answer (logical verification); Quality Context/Trace; stage metrics; extension points; offline feedback loop; compatibility with 014–017

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in application/core; infra behind interfaces; no inward imports | ✅ Strengthens stage boundaries and dependency honesty; no inward infra coupling introduced |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ Spec/plan under `specs/018-…`; cross-cutting quality justified in Complexity Tracking |
| G3 SOLID / Plugins | Externals via interfaces; Composition wires | ✅ Extension points preserve Composition exclusivity; providers remain swappable |
| G4 Async + Types | Async I/O; typed public APIs | ✅ Unchanged platform norms; not redesigned here |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations | ✅ Central focus — citations, rerank-as-disable-safe stage, prompt versioning retained |
| G6 Testing | Unit/integration planned for changed behavior | ✅ Architecture validation gates defined; concrete test authorship deferred to tasks |
| G7 Observability | Structured logging + metrics at boundaries | ✅ Quality Trace / Quality Context / stage metrics are first-class design |
| G8 Security | No secrets in artifacts | ✅ No secrets; no auth redesign |
| G9 Performance | Long work in Celery; no unjustified sync work | ✅ No ingest/answer latency program; request-path eval forbidden (§18) |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ No stack change |

## Project Structure

### Documentation (this feature)

```text
specs/018-rag-quality-architecture/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1 — quality architecture entities
├── quickstart.md        # Phase 1 — architecture validation guide
├── contracts/           # Phase 1 — normative contracts
│   ├── query-understanding-handoff.md
│   ├── retrieval-quality.md
│   ├── evidence-and-context-quality.md
│   ├── answer-grounding.md
│   ├── quality-continuity.md
│   ├── quality-observability.md
│   └── compatibility.md
├── spec.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

This plan does **not** redefine source layout. Physical packages remain non-normative. Future implementation may map logical owners to modules after `/speckit-tasks` authorization — not in this plan.

```text
src/                     # existing platform (layout non-normative for this plan)
tests/                   # existing test tree; future gates may reuse 014 suites
specs/004…017/           # related Spec Kit features (parse, stages, eval, governance, ingest)
.specify/memory/         # constitution
```

**Structure Decision**: Documentation-only deliverables for Phase 0–1. No new source tree is introduced by planning.

## Architecture Design

### Design stance

| Prescribe | Do not prescribe |
|-----------|------------------|
| Stage quality obligations and ownership | Algorithms, formulas, thresholds |
| Cross-stage contracts C1–C12 | Code modules, class diagrams, ADRs |
| Quality Context / Quality Trace shape (logical) | Persistence schema or wire format |
| Strategy architecture & candidate lifecycle ownership | Provider or model selection |
| Claim-level grounding & no-answer conditions | Prompt text or implementation heuristics |
| Offline feedback loop from 014 | Inline/runtime evaluation ownership |
| Extension points preserving sole-owner | Parallel quality pipelines |

### Quality pipeline (normative summary)

See [spec.md](./spec.md) Canonical Quality Pipeline. Accompanying artifacts: Quality Context (cumulative state) and Quality Trace (append-only sections).

### Ownership map (normative — no reassignment)

| Concern cluster | Owner (016) | 018 extension |
|-----------------|-------------|---------------|
| Query understanding | Canonical Query Understanding Owner | Understood Query quality signals |
| Retrieval planning | Canonical Retrieval Plan Owner | Strategy registry/policies; no re-parse |
| Retrieval execution | Canonical Retrieval Owner | Candidate lifecycle + score calibration |
| Evidence organization | Canonical Evidence Owner | Evidence quality model; coverage; missing-evidence |
| Context assembly | Canonical Context Owner | Priority model; compression policy |
| Answer generation | Canonical Answer Generation Owner | Logical verification; claim grounding; no-answer |
| Offline evaluation | Offline Evaluation Owner | Feedback source only (014) |
| Composition wiring | Composition | Extension wiring exclusivity |

### Compatibility summary

| Feature | Plan stance |
|---------|-------------|
| 014 | Offline authority; metrics not redefined; feedback → configuration only |
| 015 | Dual-run transitional; no permanent second answer path |
| 016 | Sole-owner / M0 freeze binding; no new quality owner |
| 017 | Ingest orthogonal; shared observability vocabulary only |

Detailed normative text: [contracts/compatibility.md](./contracts/compatibility.md).

## Validation Strategy

Aligned with spec Success Criteria. Runnable architecture checks are listed in [quickstart.md](./quickstart.md).

| Category | Proves |
|----------|--------|
| Ownership | Every §1–20 concern maps to one primary owner |
| Continuity | C1–C12 attribute bad-answer vignettes correctly |
| Modularity | Dual-path / mega-stage / eval-as-runtime-owner rejectable |
| Observability | Trace sections and Quality Context fields identifiable |
| Offline authority | 014 remains gate; no competing golden metric definitions |
| Grounding | Claim-level rule and no-answer conditions stakeholder-readable |

## Complexity Tracking

| Violation / Tension | Why Needed | Simpler Alternative Rejected Because |
|---------------------|------------|--------------------------------------|
| Cross-cutting quality architecture (vs narrow feature slice) | Answer quality depends on continuity across stages | Per-stage local tweaks without contracts recreate silent quality drops |
| Deferred physical mapping & algorithms | Spec forbids implementation/algorithm content in this feature | Naming winners or formulas now violates Out of Scope and 016 AP12 |
| Logical verification inside Answer (not separate owner) | Claim grounding needs a home without a sixth owner | Separate verification pipeline would violate sole-owner / C8 |

## Post-Design Constitution Re-Check

| Gate | Post-design | Notes |
|------|-------------|-------|
| G1–G5, G7–G10 | ✅ | Design reinforces RAG standards, citations, observability; no stack/perf/security expansion |
| G6 | ✅ | Architecture validation defined in quickstart; concrete test authorship deferred to `/speckit-tasks` |
| G2 | ✅ with justification | Cross-cutting quality feature; scoped under `specs/018-…` with co-located artifacts |
