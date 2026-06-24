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
from utils.rerank import get_reranker

# Import metrics setup
from utils.metrics import RAG_RERANK_STARTUP_LATENCY, setup_metrics

logger = logging.getLogger("uvicorn")
app = FastAPI()
frontend_dir = Path(__file__).resolve().parent / "frontend"

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Setup Prometheus metrics
setup_metrics(app)

async def startup_span():
    settings = get_settings()

    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"

    app.db_engine = create_async_engine(postgres_conn)
    app.db_client = sessionmaker(
        app.db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Idempotently ensure auxiliary indexes (e.g. GIN on chunk_metadata) exist
    # without requiring a manual Alembic migration on already-deployed DBs.
    await ensure_startup_indexes(app.db_engine)

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(config=settings, db_client=app.db_client)

    # generation client
    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id = settings.GENERATION_MODEL_ID)

    # embedding client
    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                             embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    # vector db client
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    await app.vectordb_client.connect()

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
    app.db_engine.dispose()
    await app.vectordb_client.disconnect()

app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)

app.include_router(base.base_router)
app.include_router(projects.projects_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)


@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(frontend_dir / "index.html")
