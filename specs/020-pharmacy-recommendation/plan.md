# Implementation Plan: Pharmacy Recommendation Capability

**Branch**: `enhance/query` (feature directory independent) | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-pharmacy-recommendation/spec.md`

**Note**: This plan is architecture and Domain Pack extension design for recommend-mode on the sole Answer + Retrieval path. It does **not** authorize a Recommendation Service, Recommendation API, new pipeline, or new sole owner ([ADR-020-001](./governance/adr-020-001-recommendation-as-capability.md)).

---

## Summary

Enable **need-based pharmacy recommendations** (“دواء للحموضة؟”) as a **Domain Pack capability** composed on the existing Query Understanding → Retrieval → Evidence → Context → Answer path.

Technical approach (from [research.md](./research.md)):

1. Extend pharmacy Query Understanding with recommend intent + optional **Need Frame**.
2. Govern matching via a **Symptom Taxonomy** and product **indication tags** (ingestible metadata).
3. Constrain hybrid retrieval on the sole path; compose a **Recommendation Score** from named signals (weights in pack **Recommendation Policy**).
4. Apply extensible **Safety Model** filtering (v1 subset OK) and **Product Identity Rules**.
5. Generate answers under **Explanation Policy** (evidence-only; frozen `/answer` content).
6. Record **Recommendation Trace** on 018-aligned quality/diagnostic surfaces.
7. Define recommend **eval metric catalog**; **019 owns implementation** of profiles/gates.

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic, Celery; existing LLM / embedding / vector / reranker factories

**Storage**: PostgreSQL + pgvector (primary); chunk/product metadata for indication tags, safety labels, product identity; Domain Pack YAML under `src/fields/pharmacy/`

**Testing**: pytest + pytest-asyncio; unit tests for taxonomy/mapping, safety filter, ranking signal composition, identity rules, corpus-boundedness; architecture/contract tests; integration smoke on `/answer` without schema change

**Target Platform**: Linux server / Docker Compose (AlgoRAG production stack)

**Project Type**: Web service (FastAPI) + Domain Pack configuration; capability extension (not a new deployable service)

**Performance Goals**: Recommend-mode MUST remain within existing answer-path latency envelopes; no mandatory extra LLM round-trip beyond existing parse/compose stages unless policy explicitly allows and budgets are documented in tasks

**Constraints**:
- ADR-020-001 / 016 M0: no Recommendation Service, API, parallel path, or new sole owner
- 015 frozen external `/answer` field-level contract
- 018 grounding + Quality Context/Trace expectations
- 019 owns eval runners/profiles/metric implementation
- Ranking weights and recommendation count bounds are **Policy-owned** (not hardcoded in this plan)
- Safety Model v1 MAY use a subset of dimensions

**Scale/Scope**: Pharmacy Domain Pack recommend-mode: Need Frame, Symptom Taxonomy, indication tags, logical flow composition, ranking signals, safety, identity, policy/explanation, trace/explainability, 019 metric catalog bridge; ~56-product corpus as initial coverage target; other verticals out of scope

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ✅ Pack + application extensions; no infra leakage mandated |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ `specs/020-…` + pharmacy pack + tests under existing trees |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ✅ No new provider type required; reuse LLM/vector/reranker factories |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic schemas | ✅ Internal models/types only; no public API schema break |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ Logical flow reuses hybrid + rerank; citations required |
| G6 Testing | Unit and integration tests planned for changed behavior | ✅ See Validation Strategy |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ Recommendation Trace / quality context; correlation ids |
| G8 Security | No secrets in code; input validation; parameterized SQL | ✅ No new secret surface; metadata filters parameterized |
| G9 Performance | Long work in Celery; batching/pooling considered | ✅ Answer-path only; taxonomy/tag curation offline; ingest remains Celery |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ Unchanged |

*Any unchecked gate requires justification in Complexity Tracking below.*

**Pre-Phase-0 gate result**: PASS

---

## Project Structure

### Documentation (this feature)

```text
specs/020-pharmacy-recommendation/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/              # Phase 1
│   ├── compatibility.md
│   ├── ownership-and-flow.md
│   ├── need-frame-and-taxonomy.md
│   ├── ranking-and-policy.md
│   ├── safety-and-identity.md
│   ├── explainability-and-trace.md
│   └── evaluation-bridge.md
├── governance/
│   └── adr-020-001-recommendation-as-capability.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md                # NOT created by /speckit-plan
```

### Source Code (repository root)

Extension points (existing trees — no new top-level service package):

```text
src/fields/pharmacy/          # Domain Pack: taxonomy, policy, parser, retrieval, answer_generation
src/fields/generic/           # Shared baselines merged under pack
src/core/query_parser/        # Query Understanding / Need Frame population
src/services/rag/             # Sole orchestrator + retrieval adapters (constraints, ranking signals)
src/core/answer_generation/   # Explanation Policy / recommend answer composition
src/stores/vectordb/          # Metadata filters / hybrid search (existing providers)
tests/unit/                   # Taxonomy, safety, ranking composition, identity, corpus-boundedness
tests/integration/            # /answer recommend-mode smokes (frozen contract)
tests/architecture/           # ADR-020-001 / sole-path guards (as tasks define)
```

**Structure Decision**: Single AlgoRAG web-service monorepo. Recommendation is **pack + stage extensions** under existing Query Understanding, Retrieval, and Answer ownership. No `services/recommendation/` production package and no new route module for recommend.

---

## Architecture Design

### Design stance

| Stance | Statement |
|--------|-----------|
| Capability | Recommend-mode is a pharmacy Domain Pack capability |
| Sole path | Composes existing stages only ([ownership-and-flow](./contracts/ownership-and-flow.md)) |
| Contract | Frozen `/answer` request/response fields ([compatibility](./contracts/compatibility.md)) |
| Ranking | Named signals; Policy owns weights ([ranking-and-policy](./contracts/ranking-and-policy.md)) |
| Safety | Extensible model; v1 subset allowed ([safety-and-identity](./contracts/safety-and-identity.md)) |
| Explain | Evidence-only user text; operator trace for signals ([explainability-and-trace](./contracts/explainability-and-trace.md)) |
| Eval | Metric catalog here; implementation under 019 ([evaluation-bridge](./contracts/evaluation-bridge.md)) |

### Logical flow (normative summary — not a new pipeline)

```text
Need → Need Normalization → Symptom Taxonomy Mapping → Candidate Constraints
  → Metadata Filtering → Hybrid Retrieval → Fusion → Reranking
  → Safety Filtering → Recommendation Ranking → Answer Generation
```

See [contracts/ownership-and-flow.md](./contracts/ownership-and-flow.md).

### Ownership map (normative — no reassignment)

| Concern | Owner (016) | 020 role |
|---------|-------------|----------|
| Recommend intent / Need Frame | Query Understanding | Extend pharmacy parser/pack |
| Taxonomy / indication tags / policy YAML | Domain Pack (002) | Authoritative pack artifacts |
| Constraints, hybrid, fusion, rerank, ranking signals | Retrieval | Compose on sole retrieval path |
| Safety filter + identity rules | Pack policy + Retrieval/Answer handoff | No new owner |
| Recommend answer + Explanation Policy | Answer Generation | Content + prompts/policy only |
| Recommendation Trace | Answer/Quality surfaces (018) | Diagnostics, not public API |
| Recommend metrics / profiles / gates | Evaluation (019) | Catalog requirements from 020 |

### Compatibility summary

- **015**: No new endpoint; no rename/remove of frozen answer fields.
- **016 / M0 / ADR-020-001**: No parallel path, service, or sole owner.
- **018**: Grounding + trace expectations apply to recommend-mode.
- **019**: Hosts recommend profile/golden/metric implementation.

---

## Validation Strategy

Architecture and future implementation validation (details in [quickstart.md](./quickstart.md)):

1. **Sole-path / ADR drill** — confirm no service/API/pipeline/owner creep.
2. **Frozen contract drill** — recommend answers still use `signal` / `answer` / `needs_clarification` only at the wire.
3. **Taxonomy + Need Frame drill** — many-to-many / ambiguity → clarification.
4. **Ranking signal drill** — reviewable contributions without fixed weights in architecture.
5. **Safety subset drill** — pregnancy/breastfeeding v1; unknown ≠ safe.
6. **Identity drill** — brand/line/strength/package neither false-duplicate nor false-merge.
7. **Explanation policy drill** — no hidden-score storytelling; citations present.
8. **019 bridge drill** — metric catalog mapped to an evaluation profile shape (implementation later).

---

## Complexity Tracking

> No Constitution Check violations requiring justification.

| Topic | Why Called Out | Simpler Alternative Rejected Because |
|-------|----------------|--------------------------------------|
| Logical flow section in docs | Reviewability of concern order | Omitting flow → teams invent a parallel pipeline |
| Extensible Safety Model now | Avoid pregnancy-only dead-end model | Hard-coding two dimensions → costly redesign |
| Ranking as signal composition | Reviewable & explainable (spec) | Single opaque score → fails explainability / 018 attribution |
| Eval metrics listed in 020 | Spec defines *what*; 019 implements | Duplicating runners in 020 → parallel eval ownership |

---

## Post-Design Constitution Re-Check

| Gate | Post-design |
|------|-------------|
| G1–G4 | ✅ Boundaries and types preserved; no public API break |
| G5 | ✅ Hybrid + rerank + citations + versioned pack prompts/policies |
| G6 | ✅ Unit/integration/architecture validation planned |
| G7 | ✅ Trace/explainability contract |
| G8–G10 | ✅ No secrets; answer-path; stack unchanged |

**Gate result**: PASS — proceed to `/speckit-tasks`; unresolved clarifications: none (see [research.md](./research.md)).
