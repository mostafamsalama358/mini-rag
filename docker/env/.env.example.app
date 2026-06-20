APP_NAME="mini-RAG"
APP_VERSION="0.1"

FILE_ALLOWED_TYPES=["text/plain", "application/pdf"]
FILE_MAX_SIZE=10
FILE_DEFAULT_CHUNK_SIZE=512000 # 512KB
TEXT_CHUNK_SIZE=400
TEXT_CHUNK_OVERLAP=80
TEXT_CHUNK_MIN_SIZE=200
TEXT_CHUNK_MAX_SIZE=1000
INDEXING_CHUNK_PAGE_SIZE=100
VECTOR_DB_INSERT_BATCH_SIZE=100
VERTEX_EMBEDDING_BATCH_DELAY_SECONDS=2

POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=minirag_postgres_2222
POSTGRES_HOST=pgvector
POSTGRES_PORT=5432
POSTGRES_MAIN_DATABASE=minirag

# ========================= LLM Config =========================
# GENERATION_BACKEND / EMBEDDING_BACKEND: OPENAI | COHERE | VERTEX
GENERATION_BACKEND="VERTEX"
EMBEDDING_BACKEND="VERTEX"

OPENAI_API_KEY="key___"
OPENAI_API_URL=""
COHERE_API_KEY=""

VERTEX_PROJECT_ID="your-gcp-project-id"
VERTEX_LOCATION="us-central1"
# Path inside the container; mount your JSON key via docker-compose
GOOGLE_APPLICATION_CREDENTIALS="/app/gcp-credentials.json"

GENERATION_MODEL_ID_LITERAL=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
GENERATION_MODEL_ID="gemini-2.5-flash"
EMBEDDING_MODEL_ID="text-multilingual-embedding-002"
EMBEDDING_MODEL_SIZE=768

INPUT_DAFAULT_MAX_CHARACTERS=1024
GENERATION_DAFAULT_MAX_TOKENS=2048
GENERATION_DAFAULT_TEMPERATURE=0.1

# ========================= Vector DB Config =========================
VECTOR_DB_BACKEND_LITERAL = ["QDRANT", "PGVECTOR"]
VECTOR_DB_BACKEND = "PGVECTOR"
VECTOR_DB_PATH = "qdrant_db"
VECTOR_DB_DISTANCE_METHOD = "cosine"
VECTOR_DB_PGVEC_INDEX_THRESHOLD = 100

# ========================= Template Config =========================
PRIMARY_LANG = "en"
DEFAULT_LANG = "en"

# ========================= OCR Config =========================
# Gemini OCR uses Vertex AI (same GCP credentials as GENERATION_BACKEND=VERTEX).
OCR_GEMINI_MODEL_ID="gemini-2.5-flash"
OCR_IMAGE_SCALE=1.5
OCR_PAGE_TIMEOUT_SECONDS=180

# ========================= RAG Config =========================
# RAG_HISTORY_MODE: auto | full | minimal | user_only
RAG_HISTORY_MODE="auto"
RAG_RETRIEVAL_FETCH_MULTIPLIER=3
RAG_RRF_K=60

# ========================= Celery Task Queue Config =========================
CELERY_BROKER_URL="amqp://minirag_user:minirag_rabbitmq_2222@localhost:5672/minirag_vhost"
CELERY_RESULT_BACKEND="redis://:minirag_redis_2222@localhost:6379/0"
CELERY_TASK_SERIALIZER="json"
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_ACKS_LATE=false
CELERY_WORKER_CONCURRENCY=2
CELERY_FLOWER_PASSWORD="minirag_flower_2222"
CELERY_TASK_CLEANUP_INTERVAL_SECONDS=3600
CELERY_TASK_RETENTION_SECONDS=86400

# User identity header for project scoping (sent by frontend / API gateway)
AUTH_USER_ID_HEADER="X-User-Id"
