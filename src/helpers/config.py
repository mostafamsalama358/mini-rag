from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str

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

    OPENAI_API_KEY: str = None
    OPENAI_API_URL: str = None
    COHERE_API_KEY: str = None
    VERTEX_PROJECT_ID: str = None
    VERTEX_LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: str = None
    VERTEX_EMBEDDING_BATCH_DELAY_SECONDS: int = 2
    VERTEX_EMBEDDING_RATE_LIMIT_RETRIES: int = 10
    VERTEX_EMBEDDING_RATE_LIMIT_RETRY_WAIT_SECONDS: int = 60

    GENERATION_MODEL_ID_LITERAL: List[str] = None
    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None
    INPUT_DAFAULT_MAX_CHARACTERS: int = None
    GENERATION_DAFAULT_MAX_TOKENS: int = 2048
    GENERATION_DAFAULT_TEMPERATURE: float = None

    VECTOR_DB_BACKEND_LITERAL: List[str] = None
    VECTOR_DB_BACKEND : str
    VECTOR_DB_PATH : str
    VECTOR_DB_DISTANCE_METHOD: str = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    OCR_IMAGE_SCALE: float = 1.5
    OCR_PAGE_TIMEOUT_SECONDS: int = 120
    OCR_GEMINI_MODEL_ID: str = None

    RAG_HISTORY_MODE: str = "auto"
    RAG_RETRIEVAL_FETCH_MULTIPLIER: int = 3
    RAG_RRF_K: int = 60

    # Celery Configuration
    CELERY_BROKER_URL: str = None
    CELERY_RESULT_BACKEND: str = None
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_TASK_TIME_LIMIT: int = 600
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_FLOWER_PASSWORD: str = None
    CELERY_TASK_CLEANUP_INTERVAL_SECONDS: int = 3600
    CELERY_TASK_RETENTION_SECONDS: int = 86400

    AUTH_USER_ID_HEADER: str = "X-User-Id"

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
