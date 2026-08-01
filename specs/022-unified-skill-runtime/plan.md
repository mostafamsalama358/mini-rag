# Implementation Plan: Unified Skill Runtime

**Branch**: `enhance/query` (feature directory independent) | **Date**: 2026-07-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-unified-skill-runtime/spec.md`

**Note**: This plan completes Skills as **configuration for the Unified Runtime** ([ADR-022-001](./governance/adr-022-001-skills-as-unified-runtime-configuration.md)). It does **not** authorize a Skill Service, separate Skill runtime, dual runtime, Skill-specific pipelines, or a revived legacy Skill executor.

---

## Summary

Feature **021** delivered Skill-first behavior on the **legacy** answer path (`pipeline/router.py` forces `legacy_executor` when packs have Skills). Feature **022** removes that bypass and remaining debt so Skills configure a single unified pipeline:

1. **One pipeline** — Skill traffic uses unified orchestrator only (no Skill → legacy executor).
2. **SkillExecutionContext sole contract** — immutable context + immutable stage results; remove QueryPlan `plan_field` / `plan_operation` bridge for Skill execution.
3. **True strategy plugins** — Strategy Registry → `RetrievalStrategy.execute()`; no engine `if strategy == …` branches.
4. **Declarative stages** — PipelineBuilder registers Validation → Entity Parse → Retrieval → Generation → Formatting (extensible without orchestrator edits).
5. **God-object elimination** — `answer_service` ceases to own full Skill orchestration; Skill Resolver + Pipeline Orchestrator + stage executors.
6. **Domain independence** — shared runtime has zero static `fields.pharmacy.*` and zero domain-field control branches; pack interfaces only.
7. **Enforceable architecture tests** — fail closed on dual-runtime, bridge return, strategy-name branching, domain coupling, context mutation.
8. **Compatibility** — additive `skill_id`, Skill IDs, packs, UI, frozen `/answer` response unchanged.

Technical approach (from [research.md](./research.md)): native Skill binding inside unified pipeline composition; stage contracts + registries; migrate retrieval/generation off QueryPlan field bridge; thin facade over `answer_service` during cutover then remove orchestration ownership.

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic; existing LLM / embedding / vector / reranker factories; Domain Pack YAML under `src/fields/`; existing `services/rag/pipeline/*` (015) and `services/rag/skills/*` (021)

**Storage**: Unchanged (PostgreSQL + pgvector). Skills/profiles remain pack YAML. No new DB sole-source for Skills.

**Testing**: pytest + pytest-asyncio; unit tests for stage contracts, strategy plugins, immutability; architecture tests under `tests/architecture/test_022_*`; integration smokes for Skill-bound `/answer` on unified mode; preserve 021 behavioral suite

**Target Platform**: Linux server / Docker Compose (AlgoRAG production stack)

**Project Type**: Web service (FastAPI) + Domain Pack configuration + existing chat UI; **architectural refactor** of Answer path (not a new deployable service)

**Performance Goals**: No intentional latency regression vs 021 Skill-bound legacy path on golden Skill scenarios; no mandatory extra LLM round-trips beyond entity-only parse + generation

**Constraints**:
- ADR-022-001 / ADR-021-001 / 016 M0: Skills configure unified runtime; no parallel Skill path or new sole owner
- 015 frozen **response** field-level contract; additive request `skill_id` unchanged ([contracts/api-compatibility.md](./contracts/api-compatibility.md))
- Remove QueryPlan bridge for Skill traffic ([contracts/skill-execution-context.md](./contracts/skill-execution-context.md))
- Strategy Registry forbids name-branching in engine ([contracts/strategy-registry.md](./contracts/strategy-registry.md))
- Declarative PipelineBuilder ([contracts/pipeline-registration.md](./contracts/pipeline-registration.md))
- Architecture tests enforceable ([contracts/architecture-tests.md](./contracts/architecture-tests.md))
- God-object elimination is a completion gate (SC-012 / A9)
- Non-goals: new Skills/domains; product citation enforcement; response-schema validation product work

**Scale/Scope**: Migrate existing pharmacy (11) + legal stub Skills onto unified runtime; five minimum real strategies (`default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup`); stage registration surfaces for future extensions (clarification, guardrails, tools, etc.) without shipping all implementations

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | Feature logic in controllers/services; infra in stores/utils; no inward imports | ✅ Application-layer pipeline/stages; providers via factories |
| G2 Feature-First | Change scoped to a feature slice with co-located tests | ✅ `specs/022-…` + `services/rag/pipeline|skills` + `tests/architecture/test_022_*` |
| G3 SOLID / Plugins | New externals implement existing interfaces; wired via factory | ✅ Stage + strategy + formatter registries (Open/Closed) |
| G4 Async + Types | Async I/O on hot paths; public APIs typed; Pydantic/dataclass contracts | ✅ Immutable context + typed stage results |
| G5 RAG Pipeline | Hybrid retrieval, reranking, prompt versioning, citations as applicable | ✅ Strategy plugins compose hybrid/semantic; Skill prompts pack-owned; citations preserved |
| G6 Testing | Unit and integration tests planned for changed behavior | ✅ See Validation Strategy + architecture-tests contract |
| G7 Observability | Structured logging + metrics at new async boundaries | ✅ skill/profile/strategy on pipeline traces |
| G8 Security | No secrets in code; input validation; parameterized SQL | ✅ Skill allow-list; pack interfaces; no new secret surfaces |
| G9 Performance | Long work in Celery; batching/pooling considered | ✅ Answer-path refactor only; packs load at startup |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker | ✅ Unchanged |

*Any unchecked gate requires justification in Complexity Tracking below.*

**Pre-Phase-0 gate result**: PASS

**Post-Phase-1 gate result**: PASS (design removes dual Skill path; strengthens plugins; no new owners)

---

## Project Structure

### Documentation (this feature)

```text
specs/022-unified-skill-runtime/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/              # Phase 1
│   ├── ownership-and-runtime.md
│   ├── skill-execution-context.md
│   ├── stage-contracts.md
│   ├── strategy-registry.md
│   ├── pipeline-registration.md
│   ├── architecture-tests.md
│   ├── extension-points.md
│   └── api-compatibility.md
├── governance/
│   └── adr-022-001-skills-as-unified-runtime-configuration.md
├── checklists/
└── tasks.md                # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/services/rag/
├── pipeline/                 # 015 unified pipeline — native Skill binding (022)
│   ├── router.py             # REMOVE Skill→legacy force; resolve Skill → unified
│   ├── orchestrator / builder# Declarative PipelineBuilder + stage registry
│   ├── legacy_executor.py    # Not reachable for Skill traffic (retire or non-Skill only)
│   └── ...
├── skills/                   # 021 Skill helpers — context, entity_parse, strategies, prompts
│   ├── context.py            # Immutable SkillExecutionContext; drop plan_field/operation
│   ├── strategies.py         # True plugins + StrategyRegistry (no engine name-branch)
│   ├── stages/               # Stage executors (validation, entity, retrieval, generation, format)
│   └── ...
├── answer_service.py         # Stop being Skill orchestration owner (facade → thin or decompose)
└── domain_helpers.py         # Pack interface loader (keep; expand as needed)

tests/
├── architecture/test_022_*.py
├── unit/services/rag/skills/
├── unit/services/rag/pipeline/
└── integration/test_022_*.py / preserved test_021_*
```

**Structure Decision**: Extend existing `services/rag/pipeline` + `services/rag/skills` (single project). No new top-level service package. Domain packs under `src/fields/{domain}/` unchanged as configuration SoT.

---

## Complexity Tracking

> No constitution gate violations. Complexity is intentional architecture cutover debt removal.

| Concern | Why Needed | Simpler Alternative Rejected Because |
|---------|------------|--------------------------------------|
| Declarative PipelineBuilder | SC-010 / FR-022 workflow-ready registration | Hardcoded orchestrator stage list — blocks extension without engine edits |
| Strategy Registry without name-branch | FR-020 / A4 | `if strategy == pair_lookup` in answer_service — domain/strategy coupling |
| God-object elimination | SC-012 completion gate | Keep answer_service as Skill owner — dual mental model, untestable stages |

---

## Phase 0 / Phase 1 Outputs

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/](./contracts/) |
| Quickstart | [quickstart.md](./quickstart.md) |
| ADR | [governance/adr-022-001-skills-as-unified-runtime-configuration.md](./governance/adr-022-001-skills-as-unified-runtime-configuration.md) |

---

## Validation Strategy

| Layer | Focus |
|-------|--------|
| Unit | Stage contracts (I/O/failure/side-effects); immutable context derive; StrategyRegistry resolve+execute; each minimum strategy distinct behavior; no plan_field bridge |
| Architecture | `test_022_*`: no pharmacy imports in shared runtime; legacy Skill path unreachable; no QueryPlan bridge; no strategy-name / domain-field branching; stages do not mutate context; new strategy = register only |
| Integration | Skill-enabled pack answers in **unified** mode with `skill_id`; missing/unknown skill; UI unchanged; frozen response fields |
| Audit | Post-implement architecture audit (spec validation checklist) with PASS/PARTIAL/FAIL from code paths |

---

## Implementation Phases (for `/speckit-tasks`)

1. **Native Skill binding on unified pipeline** — remove router Skill→legacy force; resolve Skill → SkillExecutionContext into pipeline context
2. **Stage contracts + PipelineBuilder** — register Validation, EntityParse, Retrieval, Generation, Formatting; independent stage tests
3. **Remove QueryPlan bridge** — drop `plan_field`/`plan_operation`; retrieval/capability consume SkillExecutionContext only
4. **Strategy Registry plugins** — implement real `default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup`; eliminate engine name-branches
5. **God-object cutover** — move orchestration out of `answer_service`; thin compatibility facade if needed
6. **Domain independence sweep** — pack interfaces only; architecture scan clean
7. **Architecture tests + migration notes** — fail-closed gates; preserve API/UI/Skill IDs; post-impl audit

---

## Next Command

`/speckit-tasks` — generate dependency-ordered implementation tasks from this plan.
