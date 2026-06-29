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
