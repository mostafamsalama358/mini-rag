"""
main.py — Application Entry Point
====================================
.NET Equivalent: Program.cs

This file is the startup script for the FastAPI web application.
It is responsible for:
  1. Creating the app instance       → WebApplication.CreateBuilder(args)
  2. Wiring infrastructure singletons → builder.Services.AddSingleton<T>()
  3. Registering startup/shutdown     → IHostedService.StartAsync / StopAsync
  4. Mounting routes                  → app.MapControllerRoute(...)

Key difference from .NET:
  Python/FastAPI does NOT have a built-in DI container like IServiceCollection.
  Instead, shared singletons (DB engine, LLM clients, etc.) are attached
  directly as attributes on the `app` object (e.g. app.db_client, app.reranker).
  Routes then read them from `request.app.<attribute>`.
"""
from pathlib import Path
import logging
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routes import base, data, nlp, projects
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from models.db_schemes import RetrievedDocument
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from helpers.db_indexes import ensure_startup_indexes
from helpers.hf_auth import configure_hf_from_settings
from utils.rerank import get_reranker

# Import metrics setup
from utils.metrics import RAG_RERANK_STARTUP_LATENCY, setup_metrics

logger = logging.getLogger("uvicorn")

# FastAPI app instance — equivalent to WebApplication built from WebApplicationBuilder.
app = FastAPI()

frontend_dir = Path(__file__).resolve().parent / "frontend"

if frontend_dir.exists():
    # Serve the built React/HTML frontend from /static — equivalent to app.UseStaticFiles().
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Setup Prometheus metrics
setup_metrics(app)

async def startup_span():
    """
    Application startup hook — runs once before the server accepts requests.
    .NET Equivalent: IHostedService.StartAsync(CancellationToken)

    This method:
      - Reads configuration (like IConfiguration / IOptions<T>)
      - Creates the DB connection pool (like AddDbContextPool<T>)
      - Instantiates all infrastructure singletons and attaches them to `app`
        (like builder.Services.AddSingleton<ILLMClient, OpenAIClient>())
    """
    settings = get_settings()  # Equivalent to IOptions<AppSettings> resolved from DI.
    configure_hf_from_settings(settings)

    # Build the PostgreSQL async connection string.
    # Equivalent to: "Server=...;Database=...;User Id=...;Password=...;"
    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"

    # Create the SQLAlchemy async engine — equivalent to registering a DbContext pool.
    # pool_size / max_overflow control the connection pool (like MinPoolSize / MaxPoolSize).
    app.db_engine = create_async_engine(
        postgres_conn,
        pool_size=4,
        max_overflow=8,
        pool_pre_ping=True,  # Validates connections before use — like connection resilience.
    )

    # `sessionmaker` is a SESSION FACTORY — a callable that creates a new DB session.
    # Equivalent to IDbContextFactory<AppDbContext> in EF Core.
    # Usage: `async with app.db_client() as session:` creates one unit-of-work session.
    app.db_client = sessionmaker(
        app.db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Idempotently ensure auxiliary indexes (e.g. GIN on chunk_metadata) exist
    # without requiring a manual Alembic migration on already-deployed DBs.
    await ensure_startup_indexes(app.db_engine)

    # Factories resolve the correct provider implementation from config.
    # Equivalent to: services.AddSingleton<ILLMClient>(provider => factory.Create(config["backend"]))
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(config=settings, db_client=app.db_client)

    # Singleton: text generation client (e.g. OpenAI, DeepSeek, Vertex AI).
    # Equivalent to: services.AddSingleton<IGenerationClient, OpenAIClient>()
    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    # Singleton: text embedding client (converts text → float vectors).
    # Equivalent to: services.AddSingleton<IEmbeddingClient, HuggingFaceClient>()
    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    # Singleton: vector database client (Qdrant, pgvector, etc.).
    # Equivalent to: services.AddSingleton<IVectorDbClient, QdrantClient>()
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    await app.vectordb_client.connect()  # Opens the persistent connection (like .OpenAsync()).

    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )
    rerank_backend = (getattr(settings, "RAG_RERANKER_BACKEND", "unknown") or "unknown").lower()
    load_started = time.perf_counter()
    app.reranker = get_reranker(settings)
    load_elapsed = getattr(app.reranker, "load_duration_seconds", time.perf_counter() - load_started)
    RAG_RERANK_STARTUP_LATENCY.labels(backend=rerank_backend, stage="load").observe(load_elapsed)

    warmup_elapsed = 0.0
    if getattr(settings, "RAG_ENABLE_RERANKER", False) and getattr(
        settings, "RAG_RERANKER_WARMUP_ON_STARTUP", True
    ):
        warmup_started = time.perf_counter()
        warmup = getattr(app.reranker, "warmup", None)
        if callable(warmup):
            await warmup()
            warmup_elapsed = getattr(
                app.reranker, "warmup_duration_seconds", time.perf_counter() - warmup_started
            )
        elif rerank_backend == "bge":
            await app.reranker.rerank(
                "warmup",
                [RetrievedDocument(text="warmup", score=0.0, metadata={})],
            )
            warmup_elapsed = time.perf_counter() - warmup_started
        if warmup_elapsed > 0:
            RAG_RERANK_STARTUP_LATENCY.labels(backend=rerank_backend, stage="warmup").observe(
                warmup_elapsed
            )

    logger.info(
        "Reranker startup complete: backend=%s load=%.2fs warmup=%.2fs",
        rerank_backend,
        load_elapsed,
        warmup_elapsed,
    )


async def shutdown_span():
    """
    Application shutdown hook — runs after the server stops accepting requests.
    .NET Equivalent: IHostedService.StopAsync(CancellationToken)
    """
    app.db_engine.dispose()              # Close all DB connections in the pool.
    await app.vectordb_client.disconnect()  # Gracefully close the vector DB connection.

# Register the lifecycle hooks on the app.
# Equivalent to: builder.Services.AddHostedService<AppLifetimeService>()
app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)

# Register all route groups — equivalent to app.MapControllerRoute() / UseEndpoints().
# Each router is defined in routes/*.py and groups related endpoints by prefix.
app.include_router(base.base_router)          # Health check / base routes
app.include_router(projects.projects_router)  # /api/v1/projects
app.include_router(data.data_router)          # /api/v1/data
app.include_router(nlp.nlp_router)            # /api/v1/nlp


@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(frontend_dir / "index.html")

@app.get("/admin", include_in_schema=False)
async def serve_admin():
    return FileResponse(frontend_dir / "admin.html")
