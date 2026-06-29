"""
helpers/config.py — Configuration Settings
===========================================
.NET Equivalent: appsettings.json + IOptions<AppSettings> + DI Singleton Registration

This file defines the `Settings` class using Pydantic, which automatically
loads configuration from environment variables and the `.env` file.

The `get_settings()` function uses `@lru_cache` to ensure the settings
are only loaded once and cached, essentially acting like a DI Singleton
registration for the configuration object.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int
    TEXT_CHUNK_SIZE: int = 800
    TEXT_CHUNK_OVERLAP: int = 120
    TEXT_CHUNK_MIN_SIZE: int = 200
    TEXT_CHUNK_MAX_SIZE: int = 1000
    INDEXING_CHUNK_PAGE_SIZE: int = 100
    VECTOR_DB_INSERT_BATCH_SIZE: int = 100

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_URL: str = "https://api.deepseek.com"
    COHERE_API_KEY: Optional[str] = None
    VERTEX_PROJECT_ID: Optional[str] = None
    VERTEX_LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    VERTEX_EMBEDDING_BATCH_DELAY_SECONDS: int = 2
    VERTEX_EMBEDDING_RATE_LIMIT_RETRIES: int = 10
    VERTEX_EMBEDDING_RATE_LIMIT_RETRY_WAIT_SECONDS: int = 60

    GENERATION_MODEL_ID_LITERAL: Optional[List[str]] = None
    GENERATION_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_SIZE: Optional[int] = None
    INPUT_DAFAULT_MAX_CHARACTERS: Optional[int] = None
    GENERATION_DAFAULT_MAX_TOKENS: int = 2048
    GENERATION_DAFAULT_TEMPERATURE: Optional[float] = None

    VECTOR_DB_BACKEND_LITERAL: Optional[List[str]] = None
    VECTOR_DB_BACKEND : str
    VECTOR_DB_PATH : str
    VECTOR_DB_DISTANCE_METHOD: Optional[str] = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    OCR_IMAGE_SCALE: float = 1.5
    OCR_PAGE_TIMEOUT_SECONDS: int = 120
    OCR_ENGINE: str = "gemini"
    OCR_GEMINI_MODEL_ID: Optional[str] = None

    RAG_HISTORY_MODE: str = "auto"
    # Over-fetch multiplier for expansion queries. The initial retrieval pass
    # uses RAG_RETRIEVAL_CANDIDATES instead (see below).
    RAG_RETRIEVAL_FETCH_MULTIPLIER: int = 3
    RAG_RRF_K: int = 60
    # When true, async request paths use the native async LLM/embedding client
    # instead of blocking the event loop with the sync SDK. Default off to
    # preserve existing behavior; enable for production async deployments.
    LLM_USE_ASYNC: bool = True
    # Soft cap (in characters) for the prompt's document context. When the
    # joined document text exceeds this, the lowest-ranked documents are
    # dropped to stay within budget. 0 disables the guard.
    RAG_PROMPT_CHAR_BUDGET: int = 0
    # Master toggle for hybrid dense + sparse retrieval. When true, dense
    # vector search and PostgreSQL full-text search run concurrently and
    # are fused via classical Reciprocal Rank Fusion. Replaces the older
    # RAG_ENABLE_BM25 setting (which is kept as a backward-compatible alias
    # when RAG_ENABLE_HYBRID_SEARCH is not explicitly set).
    RAG_ENABLE_HYBRID_SEARCH: bool = True
    # Legacy alias for RAG_ENABLE_HYBRID_SEARCH. Only consulted when
    # RAG_ENABLE_HYBRID_SEARCH is not explicitly provided in the environment.
    RAG_ENABLE_BM25: bool = True
    # Fixed candidate window size for the initial retrieval pass. Both dense
    # and sparse retrieval channels fetch this many candidates. The combined
    # results are fused via RRF and then narrowed to this count before
    # cross-encoder reranking.
    RAG_RETRIEVAL_CANDIDATES: int = 30
    # When true, a cross-encoder reranker is applied after the initial
    # retrieval and RRF fusion step. Requires RAG_RERANKER_BACKEND to be
    # set to a supported provider (e.g. "cohere" or "bge").
    RAG_ENABLE_RERANKER: bool = True
    RAG_RERANKER_BACKEND: str = "bge"
    # Model used by the Cohere reranker. Defaults to the multilingual v3 model
    # which supports Arabic + English without extra configuration.
    COHERE_RERANKER_MODEL: str = "rerank-multilingual-v3.0"
    BGE_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    # Local BGE reranker runtime controls. On CPU deployments keep fp16 off
    # and use a modest batch size to avoid large latency spikes.
    RAG_RERANKER_DEVICE: str = "cpu"
    RAG_RERANKER_BATCH_SIZE: int = 8
    RAG_RERANKER_USE_FP16: bool = False
    RAG_RERANKER_MAX_CHARS: int = 1024
    # Run a one-pair inference at startup so the first user request stays fast.
    RAG_RERANKER_WARMUP_ON_STARTUP: bool = True
    # Max documents returned by the cross-encoder reranker. When set to 0 or
    # None, all input candidates are returned (just re-ordered). Defaults to
    # 5 to keep the prompt focused on the most relevant documents.
    RAG_RERANKER_TOP_N: int = 5

    # Celery Configuration
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_TASK_TIME_LIMIT: int = 1200
    # OCR, chunking, and embedding indexing routinely exceed the global limit.
    CELERY_LONG_TASK_TIME_LIMIT: int = 3600
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_CONCURRENCY: int = 3
    CELERY_FLOWER_PASSWORD: Optional[str] = None
    CELERY_TASK_CLEANUP_INTERVAL_SECONDS: int = 3600
    CELERY_TASK_RETENTION_SECONDS: int = 86400

    AUTH_USER_ID_HEADER: str = "X-User-Id"

    HF_TOKEN: Optional[str] = None
    HF_HOME: str = "/root/.cache/huggingface"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# @lru_cache ensures this function only runs once. Subsequent calls return the cached object.
# Equivalent to: builder.Services.AddSingleton(Configuration.Get<Settings>());
@lru_cache()
def get_settings():
    return Settings()
