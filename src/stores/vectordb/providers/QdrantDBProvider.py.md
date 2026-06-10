# QdrantDBProvider.py

## What is this?

**Qdrant implementation** of `VectorDBInterface`.

Uses standalone **Qdrant** vector database (file or server).

## Why does it exist?

Alternative to PGVector when you want a dedicated vector engine.

Set `VECTOR_DB_BACKEND = QDRANT` in `.env`.

## What it does

| Action | How |
|--------|-----|
| `connect()` | Opens local Qdrant client at `VECTOR_DB_PATH` |
| `create_collection()` | Creates Qdrant collection |
| `insert_many()` | Uploads records with vectors |
| `search_by_vector()` | Qdrant similarity search |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/vectordb/VectorDBProviderFactory.py` | Created when backend is QDRANT |
| `src/controllers/BaseController.py` | `get_database_path()` for Qdrant folder |
| `docker/docker-compose.yml` | `qdrant` service on port 6333 |
| `docker/prometheus/prometheus.yml` | Scrapes Qdrant metrics |

## .NET comparison

Like using a dedicated vector search service instead of SQL vectors.
