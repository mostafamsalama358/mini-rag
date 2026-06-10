# requirements.txt

## What is this?

List of **Python packages** the project needs.

In .NET this is like `PackageReference` entries in your `.csproj` file.

## Why does it exist?

When you install dependencies:

```bash
pip install -r requirements.txt
```

Docker also uses this file in `docker/minirag/Dockerfile`.

## Main package groups

| Group | Packages | Used for |
|-------|----------|----------|
| Web API | `fastapi`, `uvicorn` | HTTP server |
| Config | `python-dotenv`, `pydantic-settings` | Read `.env` |
| Files | `python-multipart`, `aiofiles` | Upload files |
| Documents | `langchain`, `PyMuPDF` | Read PDF and TXT |
| LLM | `openai`, `cohere` | AI text and embeddings |
| Database | `SQLAlchemy`, `asyncpg`, `alembic`, `pgvector` | PostgreSQL |
| Vector DB | `qdrant-client` | Qdrant option |
| Legacy Mongo | `motor`, `pydantic-mongo` | Old MongoDB code |
| Jobs | `celery`, `redis`, `flower` | Background tasks |
| Monitoring | `prometheus-client`, `starlette-exporter` | Metrics |

## Where is it used?

| File | How |
|------|-----|
| `docker/minirag/Dockerfile` | `uv pip install -r requirements.txt` |
| Root `README.md` | Install step for local dev |
| All `src/` Python files | Import these libraries |

## .NET comparison

Run `dotnet restore` after editing — here you run `pip install -r requirements.txt`.
