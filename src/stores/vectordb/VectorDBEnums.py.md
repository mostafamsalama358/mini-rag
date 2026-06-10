# VectorDBEnums.py

## What is this?

**Enum constants** for vector database options.

## Why does it exist?

The app can use **PGVector** (PostgreSQL) or **Qdrant** for similarity search.

Enums define provider names, distance methods, and PGVector column names.

## Main enums

| Enum | Examples |
|------|----------|
| `VectorDBEnums` | `QDRANT`, `PGVECTOR` |
| `DistanceMethodEnums` | `cosine`, `dot` |
| `PgVectorTableSchemeEnums` | Column names: `id`, `text`, `vector` |
| `PgVectorDistanceMethodEnums` | Index operator classes |
| `PgVectorIndexTypeEnums` | `hnsw`, `ivfflat` |

## Where is it used?

| File | How |
|------|-----|
| `src/helpers/config.py` | `VECTOR_DB_BACKEND`, `VECTOR_DB_DISTANCE_METHOD` |
| `src/stores/vectordb/VectorDBProviderFactory.py` | Factory picks provider* |
| `src/stores/vectordb/providers/PGVectorProvider.py` | PGVector impl* |
| `src/stores/vectordb/providers/QdrantDBProvider.py` | Qdrant impl* |
| `docker/docker-compose.yml` | Runs both `pgvector` and `qdrant` services |

## .NET comparison

Like choosing between Azure AI Search vs pgvector extension in PostgreSQL.
