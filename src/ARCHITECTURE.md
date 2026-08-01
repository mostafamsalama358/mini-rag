# Mini-RAG Architecture Guide (for .NET Developers)

Welcome to the Mini-RAG project. If you are coming from a C# / .NET background, this guide maps the Python patterns used in this repository to familiar ASP.NET Core concepts to help you navigate the codebase quickly.

---

## 1. Project Structure Map

| Python Directory / File | ASP.NET Core Equivalent | Purpose |
|-------------------------|-------------------------|---------|
| `src/main.py` | `Program.cs` | The application entry point. Sets up the FastAPI app, registers singletons (DB connections, LLM providers), and configures startup/shutdown hooks (like `IHostedService`). |
| `src/helpers/config.py` | `appsettings.json` + `IOptions<T>` | Uses Pydantic `BaseSettings` to load environment variables into a strongly-typed `Settings` class. It uses a cached singleton pattern. |
| `src/routes/` | Controllers (`[ApiController]`) | Thin HTTP endpoint handlers. They receive the request, resolve dependencies from `request.app`, and delegate to business services. |
| `src/controllers/` | Services (`IService`) | **Note:** In this project, "controllers" contain business logic, not HTTP routing. Think of them as Application Services (e.g., `NLPController` is `IRagService`). |
| `src/models/` | Repositories (`IRepository`) | Data Access Layer. Classes like `ProjectModel` and `ChunkModel` encapsulate database queries using SQLAlchemy. |
| `src/models/db_schemes/` | Entities (`[Table]`) | SQLAlchemy ORM entity classes. Equivalent to EF Core entities. |
| `src/services/RAGService.py` | `IAnswerService` | A dedicated orchestrator service that handles the complex RAG pipeline (retrieval, ranking, enrichment, prompt building). |
| `src/stores/` | Factories / Providers | Infrastructure integrations (LLMs, Vector Databases) using the Factory pattern. |
| `src/core/document_intelligence/` | Document parsing application service | Generic Document Model + `ParserRegistry` + `chunk_mapper`. Format parsers (txt/csv/xlsx/pdf) emit `StructuralElement`s; domain packs configure grouping via `element_mapping` in `chunking.yaml` (no domain-name conditionals in core). |

---

## 2. Dependency Injection (DI) in FastAPI

FastAPI does not have a built-in DI container like `IServiceCollection`. Instead, this project uses the **Application State Pattern**.

In `.NET`, you would do this:
```csharp
// Program.cs
builder.Services.AddSingleton<ILLMClient, OpenAIClient>();

// Controller
public class NlpController(ILLMClient llmClient) { ... }
```

In **Mini-RAG**, singletons are attached directly to the FastAPI `app` object in `main.py` during startup:
```python
# main.py
app.generation_client = llm_provider_factory.create(...)
app.db_client = sessionmaker(...)
```

Routes then retrieve these singletons from the `Request` object:
```python
# routes/nlp.py
@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: int):
    # Resolve dependencies manually from request.app
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        # ...
    )
```

---

## 3. Database Access (SQLAlchemy vs EF Core)

This project uses **SQLAlchemy** with `asyncpg` for database access.

### Unit of Work / DbContext
In EF Core, you inject an `AppDbContext`. Here, `app.db_client` is a `sessionmaker` (a factory). You create a new session (unit of work) using an `async with` block:

```python
# Python (SQLAlchemy)
async with self.db_client() as session:
    result = await session.execute(select(Project).where(Project.project_id == 1))
    project = result.scalar_one_or_none()
```
*Equivalent .NET:*
```csharp
// C# (EF Core)
using var session = await _dbContextFactory.CreateDbContextAsync();
var project = await session.Projects.FirstOrDefaultAsync(p => p.ProjectId == 1);
```

### LINQ Equivalents
- `select(Entity)` → `dbContext.Entities`
- `.where(...)` → `.Where(...)`
- `.order_by(Entity.name.desc())` → `.OrderByDescending(e => e.Name)`
- `.offset(10).limit(5)` → `.Skip(10).Take(5)`
- `selectinload(Entity.relation)` → `.Include(e => e.Relation)` (Eager loading)
- `session.add(entity)` → `dbContext.Add(entity)`
- `await session.commit()` → `await dbContext.SaveChangesAsync()`

---

## 4. Async / Await Patterns

Python's `async`/`await` is functionally identical to C#'s `Task` based asynchrony.

### Task.WhenAll
To run tasks concurrently:
```python
# Python
results = await asyncio.gather(task1, task2)
```
*Equivalent .NET:*
```csharp
// C#
var results = await Task.WhenAll(task1, task2);
```

### Task.Run (Offloading blocking work)
If a library is synchronous (blocks the thread), it must be offloaded to a thread pool:
```python
# Python
await asyncio.to_thread(sync_function, arg1, arg2)
```
*Equivalent .NET:*
```csharp
// C#
await Task.Run(() => SyncFunction(arg1, arg2));
```

---

## 5. The RAG Pipeline Workflow

When a user asks a question (`routes/nlp.py` -> `/index/answer`), the request flows through `NLPController.answer_rag_question`, which delegates to `RAGService.py`.

The sequence is:
1. **Embedding**: Convert the user's query into a vector (`_embed_primary_query`).
2. **Retrieval**: Run a dense vector search and a sparse text search concurrently (`_fetch_dense_and_sparse_candidates`).
3. **Fusion**: Combine the results using Reciprocal Rank Fusion (`hybrid_rrf`).
4. **Expansion**: Generate sub-queries (e.g. asking for specific details or chapters) and search again (`_run_expansion_and_merge`).
5. **Reranking**: Use a Cross-Encoder LLM to score and re-sort the candidates based on actual relevance to the query.
6. **Enrichment**: For the top chunks, fetch the surrounding text (neighboring chunks from the DB) to give the LLM more context (`enrich_retrieved_documents`).
7. **Generation**: Build a prompt using the enriched context and ask the Generation LLM for the final answer.

---

## 6. Unified Production Pipeline (spec 015)

`/answer` traffic is routed by `PipelineRouter` (`services/rag/pipeline/router.py`) after
`NLPController.answer_rag_question` optionally receives a router from
`app.rag_pipeline_factory` (built in `main.py` startup via `build_rag_pipeline_factory`).

| Mode | Behavior |
|------|----------|
| `legacy` (default) | `LegacyPipelineExecutor` → existing `RAGService.answer_question` |
| `unified` | SpecKit stages: parse → plan → retrieve → evidence → context → answer |
| `shadow` | Dual-run legacy + unified concurrently; HTTP response = legacy; JSONL under `.rag_shadow/` |

Adapters in `services/rag/adapters/` map pgvector / SQL / reranker clients onto
`core/` protocols. Config: `RAG_PIPELINE_MODE`, `RAG_PIPELINE_FALLBACK_ON_ERROR`,
`RAG_PIPELINE_CANARY_PROJECT_IDS`, and per-project `config_json.pipeline_mode`.

---

## 7. Architecture Consolidation Governance (spec 016)

**Normative plan**: `specs/016-architecture-consolidation/plan.md`  
**Registries** (logical ownership — not package winners): `specs/016-architecture-consolidation/governance/`

### Principles (summary)

- One Concern = One Owner; One Production Path per Capability; One Canonical Contract per Concept
- Composition owns wiring; Infrastructure behind interfaces; Domain Packs extend without capturing core
- Cutover before retirement; lifecycle honesty for inactive capabilities
- Dual-path growth is **frozen** (M0): no new parallel production implementations without ADR

### How to find the owner

1. Open `specs/016-architecture-consolidation/governance/capability-cards.md`
2. Resolve Owner in `ownership-registry.md` (logical parties only)
3. Check `lifecycle-registry.md` for non-production / transitional subjects
4. Use `specs/016-architecture-consolidation/checklists/architecture-review.md` for PRs that change capabilities

### Domain packs

Vertical heuristics are owned by **Domain Packs**. Authors follow  
`specs/016-architecture-consolidation/governance/domain-pack-extension-guide.md`.  
Do not hardcode a vertical into core orchestration.

### PR / review obligation

Changes that introduce or modify a production capability MUST complete the architecture-review checklist (or attach an exception ADR with scope, duration, and exit criteria). Parallel production paths and hidden paths are forbidden (AP1 / AP10).

### Relationship to 015

015 is the answer **cutover vehicle** (legacy / shadow / unified). 016 is the **governance target** (sole ownership, contracts, lifecycle, retirement meaning). See `governance/relationship-to-015.md`.

---

## 8. Ingest Reliability Control Plane (spec 017)

**Normative plan**: `specs/017-scalability-reliability/plan.md`  
**Contracts**: `specs/017-scalability-reliability/contracts/`

Hardens the **sole** Application (Ingest) path — no second ingest stack (016 M0).

- Package: `services/ingest_reliability/` (lifecycle, admission, capacity, publish, orphans, …)
- Durable tables: `ingest_jobs`, checkpoints, capacity claims, operational events, logical versions, publish completions
- Process endpoints (`routes/data.py`) return additive `job_id` / `correlation_id` when enabled
- Operator surfaces: `GET /api/v1/data/ingest-jobs/{job_id}`, `POST .../cancel`
- Config: `INGEST_RELIABILITY_ENABLED`, `INGEST_OPERATIONAL_MODE`, capacity/stall/poison knobs (see `.env.example`)

---

## 9. RAG Quality Architecture (spec 018)

**Normative plan**: `specs/018-rag-quality-architecture/plan.md`  
**Registries**: `specs/018-rag-quality-architecture/governance/`  
**Contracts**: `specs/018-rag-quality-architecture/contracts/`

Extends quality contracts across Query Understanding → Planner → Engine → Evidence → Context → Answer (logical verification) **without** new production owners or parallel paths (C8 / 016 M0).

### Principles (summary)

- Contract-first continuity (C1–C12): strategy alignment, filter pushdown, dedup ladder, conflicts, citations, token efficiency, hallucination chain, modularity freeze, Understood Query authority, coverage/missing-evidence, Quality Context/Trace, claim-level grounding
- Coverage validation owned by Evidence; claim grounding / no-answer owned by Answer Generation
- Score calibration owned by Retrieval (Engine); no competing calibration authority
- Feature 014 remains offline evaluation authority and feedback source — not a request-path owner
- Architecture phase delivers registries/tests — not algorithms or pipeline implementation

### How to find the quality owner

1. Open `specs/018-rag-quality-architecture/governance/stage-ownership-map.md`
2. Confirm continuity via `continuity-contract-index.md` (C1–C12)
3. For defects: `defect-attribution-guide.md` + `failure-vignette-catalog.md`
4. Cross-check sole-owner baseline in 016 `ownership-registry.md`
5. **Never invent a “Quality Owner.”**

### PR / review obligation

Answer/retrieval quality contract changes MUST complete  
`specs/018-rag-quality-architecture/checklists/quality-architecture-review.md`  
(or 016 architecture-review / exception ADR). Reject parallel quality paths, mega-stage merges, Answer-as-sole-coverage-owner, and 014-as-runtime-owner.

### Relationship to 014–017

See `specs/018-rag-quality-architecture/governance/relationship-to-014-017.md`.

## 10. RAG Evaluation Framework (spec 019)

**Normative plan**: `specs/019-rag-evaluation-framework/plan.md`  
**Registries**: `specs/019-rag-evaluation-framework/governance/`  
**Contracts**: `specs/019-rag-evaluation-framework/contracts/`

Extends Feature 014 offline golden semantics into a full evaluation architecture (offline / shadow / monitoring) **without** a production evaluation stage or parallel answer/retrieval path (016 M0).

### Principles (summary)

- Exactly one Primary Owner per failed metric (Metric Ownership Registry)
- Evaluation Profiles bind tiers/gates/expectation classes � not numeric thresholds
- Judge Layer keeps metric identities stable across Rule / LLM / Human / Hybrid
- Dataset/Benchmark freeze + run metadata for reproducibility
- Offline gates remain merge/release authority; alerts notify; drift is categorized
- Feature 019 gates win over Feature 018 diagnostics for release decisions; 014 Faithfulness/Completeness semantics preserved
- Architecture phase delivers registries/tests � not runners, scorers, formulas, or CI YAML

### How to attribute a PR gate failure

1. Open `specs/019-rag-evaluation-framework/governance/metric-ownership-registry.md`
2. Classify via `error-taxonomy-catalog.md`
3. Optionally annotate root cause via `metric-dependency-map.md` (do not reassign Primary Owner)
4. Confirm PR freeze/gate in `evaluation-profile-index.md` + `ci-integration-summary.md`
5. Cross-check 016 `ownership-registry.md`
6. **Never invent a production Evaluation/Quality owner for traffic.**

### PR / review obligation

Evaluation-architecture contract changes SHOULD complete  
`specs/019-rag-evaluation-framework/checklists/evaluation-architecture-review.md`  
and MUST NOT violate 016 sole-owner / M0 freeze or 018 quality-architecture-review rules for parallel quality paths.

### Relationship to 014�018

See `specs/019-rag-evaluation-framework/governance/relationship-to-014-018.md`.

---

## Pharmacy Recommendation Capability (Feature 020)

Need-based pharmacy recommendations are a Domain Pack capability on the sole Answer + Retrieval path.

- ADR: `specs/020-pharmacy-recommendation/governance/adr-020-001-recommendation-as-capability.md`
- No Recommendation Service, Recommendation API, parallel pipeline, or new sole owner
- Pack artifacts under `src/fields/pharmacy/`
- Internal helpers: `src/services/rag/recommend/` (not a 016 production owner)
- Frozen `/answer` contract only; eval runners owned by 019
