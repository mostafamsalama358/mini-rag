# Implementation Plan: Production Scalability & Reliability

**Branch**: `017-scalability-reliability` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-scalability-reliability/spec.md`

## Summary

Harden the **sole production ingest path** (Application Ingest orchestration → Document Intelligence → Chunking → Persist/Index) into a production-grade, memory-bounded, recoverable pipeline with explicit job lifecycle, atomic/exactly-once publishing, versioned documents, admission/back-pressure, workload isolation, orphan recovery, and full operational auditability.

Approach:

1. Treat [spec.md](./spec.md) lifecycle, publishing, capacity, and recovery rules as normative behavior.
2. Strengthen existing Celery-based async ingest (`tasks/process_workflow.py`, `tasks/file_processing.py`, `services/process_service.py`) rather than introducing a second selectable ingest stack (016 M0 freeze).
3. Introduce durable **Ingest Job** control-plane state (lifecycle, checkpoints, publish completion, operational history) owned by Application (Ingest), with Infrastructure providers remaining behind existing interfaces.
4. Enforce stage contracts, integrity/security gates, and exactly-once Active Version activation before search visibility changes.
5. Roll out via R0–R4 governance gates; validate with golden corpus, soak/chaos/recovery suites per [quickstart.md](./quickstart.md).

Depends on Document Intelligence / chunking semantics from `006`/`007` lineage and ownership bindings from `016` (`ingest_orchestration`, `document_parsing`, `chunking_embed_text`, `persist_index`). Does not redesign Answer/Search paths.

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic, Celery (+ existing broker); Document Intelligence (`src/core/document_intelligence/`); existing embedding/vector provider factories; Prometheus metrics via `utils/metrics.py`

**Storage**: PostgreSQL + pgvector (primary). Durable job/control-plane records and operational history in PostgreSQL; unpublished intermediate artifacts remain non-searchable until atomic publish. Optional Qdrant via factory unchanged for vector backend selection.

**Testing**: pytest + pytest-asyncio; unit (`tests/unit/…/ingest_reliability/`), integration (`tests/integration/ingestion/`), contract tests for lifecycle/publish semantics, plus soak/chaos/recovery drills documented in quickstart

**Target Platform**: Linux containers via Docker Compose (existing API + worker deployment)

**Project Type**: Single backend web service (FastAPI) + Celery workers — operator-facing job visibility may extend existing process/status surfaces; no new product UI required for v1

**Performance Goals**:
- Interactive admission decision (accept / delay / reject) within existing interactive submission budget (SC-002)
- Normal-doc p95 ingest latency regression ≤ 15% vs baseline (SC-009)
- Large-document profile completes within published SLA band under declared resource budget (SC-001)
- Fairness: small-doc class not indefinitely starved when large-doc class is at limit (SC-014)

**Constraints**:
- No parallel production ingest stack (016 M0 / NFR-008)
- Memory-bounded streaming/batched processing; hard size/concurrency/duration/retry limits
- Atomic + exactly-once publish per Logical Document Version; no partial Active Version visibility
- Idempotent retry/resume; poison/dead-letter for repeated permanent failures
- Interactive ingestion capacity protected from background/maintenance/migration (FR-054)
- Secrets never in logs/audit history

**Scale/Scope**: Sole ingest path hardening across admission→publish; workload classes (small/large/maintenance/migration); operational modes; golden + stress/soak/chaos/recovery validation; R0–R4 rollout

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in application/core; infra behind interfaces; no inward imports | ✅ — Job orchestration/lifecycle in Application (Ingest); parse/chunking in core owners; providers stay in Infrastructure |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ — `specs/017-…` + ingest reliability test slices; no Answer/Search redesign |
| G3 SOLID / Plugins | Externals via interfaces; Composition wires | ✅ — No new provider families required; existing LLM/embed/vector factories reused; Composition remains wiring authority |
| G4 Async + Types | Async I/O; typed public APIs | ✅ — HTTP admission async; long work in Celery; Pydantic job/lifecycle models |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ — N/A to ingest redesign; publish quality preserves citation-ready chunk metadata from 006/007 |
| G6 Testing | Unit/integration planned for changed behavior | ✅ — See Testing + [quickstart.md](./quickstart.md) |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ — Correlation identity E2E; lifecycle/progress/mode/orphan signals (FR-018/057/058) |
| G8 Security | No secrets; input validation; parameterized SQL | ✅ — Security gates before expensive work (FR-015); tenant ownership checks |
| G9 Performance | Long work in Celery; batching/pooling | ✅ — Core of this feature; batching + back-pressure + budgets |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ — No stack replacement |

*All gates pass. No Complexity Tracking entries required.*

**Post-design re-check**: Contracts and data model remain within Application/Core/Infrastructure boundaries; no second ingest stack; Celery retained for long work. Gates still pass.

## Project Structure

### Documentation (this feature)

```text
specs/017-scalability-reliability/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── job-lifecycle.md
│   ├── publishing-semantics.md
│   ├── stage-contracts.md
│   ├── admission-capacity.md
│   ├── operational-modes.md
│   └── observability-audit.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
src/
├── routes/                      # Admission / job status presentation (extend existing process surfaces)
├── services/
│   └── process_service.py       # Ingest orchestration (harden; job control plane)
├── tasks/
│   ├── process_workflow.py      # Async workflow entry
│   ├── file_processing.py       # Parse/chunk stages
│   └── data_indexing.py         # Enrich/index/publish stages (existing indexing path)
├── core/
│   └── document_intelligence/   # Parse owner (006) — streaming/bounded + outcome classification
├── models/db_schemes/algorag/   # Durable job/history/checkpoint/version records
├── helpers/config.py            # Validated, version-aware operational config
└── utils/metrics.py             # Ingest reliability metrics

tests/
├── unit/…/ingest_reliability/
├── integration/ingestion/
└── contract/                    # Lifecycle, publish, admission contracts
```

**Structure Decision**: Single-project FastAPI + Celery layout. Control-plane durability and orchestration harden under Application (Ingest); parsing/chunking remain core owners per 016; no new top-level application package required for v1. Exact module splits are deferred to `/speckit-tasks`.

## Complexity Tracking

> No constitution violations. Empty by design.
