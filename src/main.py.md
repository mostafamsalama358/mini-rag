# main.py

## What is this?

The **main entry point** of the FastAPI application.

In .NET this is like `Program.cs` — it builds and starts the web app.

## Why does it exist?

It must:

1. Create the FastAPI `app`
2. Connect to PostgreSQL on startup
3. Create LLM clients (OpenAI, Cohere)
4. Connect to the vector database
5. Register API routes
6. Set up Prometheus metrics

## What happens on startup

| Step | Code does |
|------|-----------|
| DB | Opens async PostgreSQL connection |
| LLM | Creates generation + embedding clients |
| Vector DB | Connects to PGVector or Qdrant |
| Templates | Loads RAG prompt templates |
| Routes | Adds routers from `routes/` |

## Where is it used?

| File | How |
|------|-----|
| `docker/minirag/Dockerfile` | Runs `uvicorn main:app` |
| Root `README.md` | Dev command: `uvicorn main:app --reload` |
| `src/routes/base.py` | Router registered here |
| `src/routes/data.py` | Upload and process routes |
| `src/routes/nlp.py` | Search and RAG routes |
| `src/helpers/config.py` | Reads settings from `.env` |
| `src/utils/metrics.py` | Sets up `/metrics` endpoint |
| `src/stores/llm/LLMProviderFactory.py` | Creates AI clients |
| `src/stores/vectordb/VectorDBProviderFactory.py` | Creates vector DB client |
| `src/stores/llm/templates/template_parser.py` | RAG prompt templates |

## .NET comparison

```csharp
// Similar flow in Program.cs:
// builder.Services.AddDbContext...
// app.MapControllers();
// app.Run();
```
