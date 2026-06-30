<!--
Sync Impact Report
==================
Version change: (template/unratified) → 1.0.0
Modified principles: N/A (initial ratification from template placeholders)
Added sections:
  - Core Principles (I–IX)
  - Technology Stack & Infrastructure
  - Development Workflow & Quality Gates
  - Governance
Removed sections: None (template placeholders replaced)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated
  - .specify/templates/spec-template.md ✅ updated
  - .specify/templates/tasks-template.md ✅ updated
  - .specify/templates/commands/*.md ⚠ not present (skipped)
  - README.md ⚠ pending (still references Python 3.10; constitution mandates 3.13)
Follow-up TODOs:
  - TODO(RATIFICATION_REVIEW): Confirm 2026-06-29 as official ratification date with maintainers
  - Align README runtime version and local dev docs with Python 3.13 mandate
-->

# AlgoRAG Constitution

Production-grade governance for a generic, extensible Retrieval-Augmented Generation (RAG)
platform. This constitution defines non-negotiable architectural, quality, and operational
rules for all features, refactors, and integrations.

## Core Principles

### I. Clean Architecture

The codebase MUST follow Clean Architecture with explicit dependency direction:

- **Domain / entities** — business rules and data shapes (`models/db_schemes/`, enums)
- **Application** — use cases and orchestration (`controllers/`, `services/`)
- **Infrastructure** — external systems (`stores/`, `utils/`, Celery tasks)
- **Presentation** — HTTP and UI (`routes/`, `frontend/`)

Inner layers MUST NOT import from outer layers. Infrastructure implements interfaces
defined in application or domain boundaries (e.g., `VectorDBInterface`,
`RerankerInterface`, LLM provider contracts). Framework details (FastAPI, SQLAlchemy
session mechanics) stay at the edges; business logic MUST remain testable without a
running server or live external APIs.

**Rationale**: Preserves replaceability of providers and keeps RAG pipeline logic
independent of vendor SDKs.

### II. Feature-First Organization

New capabilities MUST be organized by feature or bounded context, not by technical
layer alone. Each feature slice MUST be independently describable, testable, and
deployable where feasible:

- Co-locate routes, application services, schemas, and feature-specific tests
- Shared cross-cutting code lives in `helpers/`, `utils/`, or `stores/` only when
  genuinely reused by two or more features
- Avoid "god" modules; split when a file exceeds a single responsibility

**Rationale**: Feature-first structure maps to user value, speeds onboarding, and
supports incremental delivery.

### III. SOLID Design

All production code MUST adhere to SOLID:

- **S**ingle Responsibility — one reason to change per class/module
- **O**pen/Closed — extend via new provider/plugin implementations, not conditional
  sprawl in callers
- **L**iskov Substitution — every provider MUST honor its interface contract
- **I**nterface Segregation — small, focused protocols (generation vs embedding vs
  vector search vs reranking)
- **D**ependency Inversion — depend on abstractions; wire concrete implementations in
  composition roots (`main.py`, `celery_runtime.py`, factories)

**Rationale**: SOLID is the enforcement mechanism for the pluggable architecture this
platform requires.

### IV. Async-First with Type Safety

- **Python 3.13** is the mandated runtime for production and CI
- I/O-bound paths (HTTP handlers, DB access, external LLM/embedding calls) MUST use
  `async`/`await` unless a blocking library is unavoidable; in that case, isolate
  blocking work (thread pool / worker process) and document the exception
- Public functions, methods, and class attributes MUST have type hints; prefer
  `typing` and `collections.abc` over untyped `Any`
- Pydantic models MUST back request/response schemas and configuration (`Settings`)

**Rationale**: Async-first maximizes throughput for concurrent RAG workloads; type hints
catch integration errors before runtime.

### V. Pluggable Provider Architecture

Infrastructure integrations MUST be swappable without modifying core RAG logic:

| Capability | Contract location | Factory / registry |
|------------|-------------------|--------------------|
| LLM generation | `stores/llm/` | `LLMProviderFactory` |
| Embeddings | `stores/llm/` | `LLMProviderFactory` |
| Vector database | `stores/vectordb/` | `VectorDBProviderFactory` |
| Reranking | `utils/rerank/` | `get_reranker()` |

Rules:

- New providers MUST implement the existing interface; registration happens in the
  factory, not in route handlers
- Provider selection MUST be configuration-driven (`helpers/config.py` / env vars)
- No provider-specific imports in `services/RAGService.py` or controllers

**Rationale**: Multi-LLM and multi-store support is a product requirement, not an
afterthought.

### VI. RAG Pipeline Standards

Every retrieval-augmented feature MUST comply with these pipeline rules:

1. **Hybrid retrieval** — combine dense vector search with sparse/keyword retrieval
   (e.g., PostgreSQL full-text + pgvector) and fuse results (RRF or equivalent)
   when `RAG_ENABLE_HYBRID_SEARCH` is enabled
2. **Reranking** — cross-encoder or API reranker applied after fusion; configurable
   via `RAG_RERANKER_BACKEND`; no-op path MUST remain valid for degraded mode
3. **Prompt versioning** — project/system prompts MUST be versioned and persisted
   (`project_prompts` or successor table); prompts MUST NOT be hard-coded in routes
4. **Source citations** — LLM responses MUST include traceable citations to retrieved
   chunks (document id, chunk id, score, excerpt metadata) in API responses
5. **Idempotency** — ingestion and indexing tasks MUST be safe to retry

**Rationale**: These behaviors define production-grade RAG quality and auditability.

### VII. Testing Discipline (NON-NEGOTIABLE)

- **Unit tests** — required for business logic, factories, fusion/rerank utilities,
  and prompt assembly; mock external providers
- **Integration tests** — required for DB migrations, pgvector queries, API contracts,
  and end-to-end ingestion → retrieval → answer flows
- Tests MUST run in CI on every PR; new features MUST NOT merge without covering
  changed behavior
- Prefer `pytest` + `pytest-asyncio`; use test containers or Docker Compose for
  PostgreSQL/pgvector integration tests
- Bug fixes MUST include a regression test when feasible

**Rationale**: Provider permutations and async pipelines are too complex for manual
verification alone.

### VIII. Observability & Structured Logging

- Use structured, machine-parseable logs (JSON or key-value) with consistent fields:
  `request_id`, `project_id`, `user_id`, `task_id`, `provider`, `latency_ms`, `status`
- Log at boundaries: HTTP ingress/egress, Celery task start/finish, retrieval counts,
  reranker latency, LLM token usage
- Prometheus metrics (`utils/metrics.py`) MUST be extended when adding latency-sensitive
  pipeline stages
- Errors MUST include exception type and correlation id; secrets and PII MUST NOT
  appear in logs

**Rationale**: Production RAG systems fail opaquely without traceable, queryable telemetry.

### IX. Security by Design

- Secrets (API keys, GCP service accounts, DB passwords) MUST live in environment
  variables or secret stores; NEVER committed to git (see `.gitignore`)
- Validate and sanitize all uploads; enforce `FILE_ALLOWED_TYPES` and `FILE_MAX_SIZE`
- Parameterize all SQL; no string-concatenated queries
- Authenticate admin and data-mutation endpoints; treat `user_id` headers as trusted
  only behind an API gateway or auth middleware in production
- Apply least-privilege IAM for cloud providers; rotate credentials on exposure
- Rate-limit or queue expensive LLM/embedding calls where appropriate

**Rationale**: RAG platforms handle user documents and third-party API keys — a high
trust surface.

### X. Performance & Scalability

- Long-running work (file parsing, OCR, embedding, bulk indexing) MUST run in Celery
  workers, not request handlers
- Batch embedding and vector inserts using configured batch sizes
  (`VECTOR_DB_INSERT_BATCH_SIZE`, provider-specific limits)
- Use connection pooling for PostgreSQL (`pool_size`, `max_overflow`, `pool_pre_ping`)
- Index pgvector columns and full-text columns per collection size thresholds
- Profile before optimizing; document p95 latency targets per endpoint in feature specs
- Cache expensive local models (BGE, rerankers) with explicit warmup controls

**Rationale**: RAG workloads are CPU/GPU and I/O heavy; async + workers + batching are
baseline requirements, not optimizations.

## Technology Stack & Infrastructure

The following stack is **mandated** unless a constitution amendment explicitly approves
a deviation:

| Layer | Technology |
|-------|------------|
| Language | Python 3.13 |
| API framework | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Database | PostgreSQL |
| Vector search | pgvector (primary); Qdrant permitted via `VectorDBProviderFactory` |
| Migrations | Alembic |
| Task queue | Celery + RabbitMQ/Redis |
| Containerization | Docker + Docker Compose |
| Frontend | Static SPA served by FastAPI (`src/frontend/`) |

Deployment artifacts MUST be reproducible from `docker/` definitions. Local development
MUST be achievable with Compose services for Postgres, broker, and workers.

## Development Workflow & Quality Gates

### Branching & specs

- Feature work MUST originate from a spec in `specs/[###-feature-name]/` produced by
  the Speckit workflow (`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`)
- Plans MUST pass the **Constitution Check** gates before implementation begins

### Code review checklist

Every PR MUST verify:

1. Clean Architecture boundaries respected (no inward imports from infrastructure)
2. New providers registered via factory, not ad-hoc instantiation
3. Type hints on public APIs
4. Unit and/or integration tests for changed behavior
5. Structured logging at new async boundaries
6. No secrets or credentials in diff
7. Celery used for any operation expected to exceed HTTP timeout budgets
8. Citations and prompt versioning preserved for RAG answer paths

### Quality gates (CI)

- `ruff` / linter clean
- `pytest` unit + integration suites pass
- Alembic migrations apply cleanly on empty and existing databases
- Docker images build successfully

### Complexity justification

Deviations from these principles (e.g., bypassing hybrid retrieval, synchronous
indexing in HTTP handlers, provider-specific logic in services) MUST be documented in
the plan's **Complexity Tracking** table with rejected simpler alternatives.

## Governance

- This constitution supersedes ad-hoc conventions in READMEs and inline comments when
  they conflict
- **Amendments** require:
  1. A PR updating `.specify/memory/constitution.md`
  2. A version bump per semantic versioning (see below)
  3. Propagation to affected templates (`plan-template.md`, `spec-template.md`,
     `tasks-template.md`) and `src/ARCHITECTURE.md` when principles change
  4. Maintainer review and explicit approval
- **Versioning policy**:
  - **MAJOR** — principle removed or redefined incompatibly
  - **MINOR** — new principle or materially expanded section
  - **PATCH** — clarifications, typos, non-semantic wording
- **Compliance review** — quarterly or before each release tag; verify provider
  interfaces, test coverage trends, and secret-scanning hygiene
- Runtime development guidance: `src/ARCHITECTURE.md`, `docker/README.md`

**Version**: 1.0.0 | **Ratified**: 2026-06-29 | **Last Amended**: 2026-06-29
