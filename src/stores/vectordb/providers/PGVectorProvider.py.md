# PGVectorProvider.py

## What is this?

**PGVector implementation** of `VectorDBInterface`.

Stores vectors inside **PostgreSQL** using the `pgvector` extension.

## Why does it exist?

Default vector backend in this project (`VECTOR_DB_BACKEND = PGVECTOR`).

One database for both relational data and vectors.

## What it does

| Action | How |
|--------|-----|
| `connect()` | Enables `CREATE EXTENSION vector` |
| `create_collection()` | Creates a table per project collection |
| `insert_many()` | Inserts rows with text + vector |
| `search_by_vector()` | SQL similarity search |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/vectordb/VectorDBProviderFactory.py` | Created when backend is PGVECTOR |
| `src/stores/vectordb/VectorDBEnums.py` | Column and index enum names |
| `docker/docker-compose.yml` | `pgvector` service |
| `src/helpers/config.py` | Distance method, index threshold |

## .NET comparison

Like storing embeddings in SQL Server with a vector column extension.
