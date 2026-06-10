# VectorDBProviderFactory.py

## What is this?

**Factory** that creates the vector database provider (PGVector or Qdrant).

## Why does it exist?

The app supports two vector stores. Settings pick one via `VECTOR_DB_BACKEND`.

This factory returns the right implementation.

## How it works

| Provider string | Returns |
|-----------------|---------|
| `"QDRANT"` | `QdrantDBProvider` (local folder) |
| `"PGVECTOR"` | `PGVectorProvider` (PostgreSQL extension) |

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | `app.vectordb_client = factory.create(...)` |
| `src/celery_app.py` | Workers get vector client in `get_setup_utils()` |
| `src/controllers/NLPController.py` | Search and index operations |
| `src/stores/vectordb/VectorDBEnums.py` | Provider name constants |
| `src/helpers/config.py` | `VECTOR_DB_BACKEND`, `EMBEDDING_MODEL_SIZE` |
| `docker/docker-compose.yml` | Runs `pgvector` and `qdrant` services |

## .NET comparison

Like choosing Azure AI Search vs pgvector via config and a factory.
