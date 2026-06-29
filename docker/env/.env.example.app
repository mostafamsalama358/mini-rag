APP_NAME="AlgoRAG"
APP_VERSION="0.1"

FILE_ALLOWED_TYPES=["text/plain", "application/pdf"]
FILE_MAX_SIZE=10
FILE_DEFAULT_CHUNK_SIZE=512000
TEXT_CHUNK_SIZE=400
TEXT_CHUNK_OVERLAP=80
TEXT_CHUNK_MIN_SIZE=200
TEXT_CHUNK_MAX_SIZE=1000
INDEXING_CHUNK_PAGE_SIZE=100
VECTOR_DB_INSERT_BATCH_SIZE=100
VERTEX_EMBEDDING_BATCH_DELAY_SECONDS=2

POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=algorag_postgres_2222
POSTGRES_HOST=pgvector
POSTGRES_PORT=5432
POSTGRES_MAIN_DATABASE=algorag

# ========================= Generation (LLM) =========================
# GENERATION_BACKEND: DEEPSEEK | OPENAI | COHERE | VERTEX
GENERATION_BACKEND=DEEPSEEK

DEEPSEEK_API_KEY=
DEEPSEEK_API_URL=https://api.deepseek.com
GENERATION_MODEL_ID=deepseek-v4-flash
GENERATION_MODEL_ID_LITERAL=["deepseek-v4-flash","deepseek-v4-pro","gemini-2.5-flash"]

# Alternate generation providers
# GENERATION_BACKEND=VERTEX
# VERTEX_PROJECT_ID=your-gcp-project-id
# VERTEX_LOCATION=us-central1
# GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
# GENERATION_MODEL_ID=gemini-2.5-flash

INPUT_DAFAULT_MAX_CHARACTERS=1024
GENERATION_DAFAULT_MAX_TOKENS=2048
GENERATION_DAFAULT_TEMPERATURE=0.1

# ========================= Embedding =========================
# EMBEDDING_BACKEND: BGE | OPENAI | COHERE | VERTEX
# BGE runs in-process — mount GPU into the app/celery container for best performance.
EMBEDDING_BACKEND=BGE
EMBEDDING_MODEL_ID=BAAI/bge-m3
EMBEDDING_MODEL_SIZE=1024

# Alternate embedding providers
# EMBEDDING_BACKEND=VERTEX
# EMBEDDING_MODEL_ID=text-multilingual-embedding-002
# EMBEDDING_MODEL_SIZE=768

# ========================= Vector DB =========================
VECTOR_DB_BACKEND_LITERAL=["QDRANT","PGVECTOR"]
VECTOR_DB_BACKEND=PGVECTOR
VECTOR_DB_PATH=qdrant_db
VECTOR_DB_DISTANCE_METHOD=cosine
VECTOR_DB_PGVEC_INDEX_THRESHOLD=100

# ========================= OCR =========================
# OCR_ENGINE: docling | gemini
OCR_ENGINE=docling
OCR_IMAGE_SCALE=1.5
OCR_PAGE_TIMEOUT_SECONDS=180
OCR_GEMINI_MODEL_ID=gemini-2.5-flash

# ========================= Language =========================
PRIMARY_LANG=ar
DEFAULT_LANG=en

# ========================= Reranker =========================
# RAG_RERANKER_BACKEND: bge | cohere
RAG_ENABLE_RERANKER=true
RAG_RERANKER_BACKEND=bge
BGE_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RAG_RERANKER_DEVICE=cpu
RAG_RERANKER_BATCH_SIZE=8
RAG_RERANKER_USE_FP16=false
RAG_RERANKER_MAX_CHARS=1024
RAG_RERANKER_WARMUP_ON_STARTUP=true
# COHERE_RERANKER_MODEL=rerank-multilingual-v3.0
# Final Top-N returned by the cross-encoder reranker (0/None = all).
RAG_RERANKER_TOP_N=5
# Benchmark local CPU settings (run from src/):
# python scripts/benchmark_bge_reranker.py

# ========================= RAG =========================
# Hybrid retrieval: dense vector search + PostgreSQL full-text search
# fused via classical Reciprocal Rank Fusion (RRF). RAG_ENABLE_BM25 is a
# legacy alias (consulted only when RAG_ENABLE_HYBRID_SEARCH is unset).
RAG_ENABLE_HYBRID_SEARCH=true
RAG_ENABLE_BM25=false
# Candidate window: both dense and sparse fetch this many candidates.
RAG_RETRIEVAL_CANDIDATES=30
# Classical RRF constant (k).
RAG_RRF_K=60
# Over-fetch multiplier for expansion queries only.
RAG_RETRIEVAL_FETCH_MULTIPLIER=3
RAG_HISTORY_MODE=auto
RAG_PROMPT_CHAR_BUDGET=0
LLM_USE_ASYNC=false

# Hugging Face — get a token at https://huggingface.co/settings/tokens
HF_TOKEN=
HF_HOME=/root/.cache/huggingface

# ========================= Celery =========================
CELERY_BROKER_URL=amqp://algorag_user:algorag_rabbitmq_2222@rabbitmq:5672/algorag_vhost
CELERY_RESULT_BACKEND=redis://:algorag_redis_2222@redis:6379/0
CELERY_TASK_SERIALIZER=json
CELERY_TASK_TIME_LIMIT=1200
CELERY_LONG_TASK_TIME_LIMIT=3600
CELERY_TASK_ACKS_LATE=false
CELERY_WORKER_CONCURRENCY=3
CELERY_FLOWER_PASSWORD=algorag_flower_2222
CELERY_TASK_CLEANUP_INTERVAL_SECONDS=3600
CELERY_TASK_RETENTION_SECONDS=86400

AUTH_USER_ID_HEADER=X-User-Id
