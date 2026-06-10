# VectorDBInterface.py

## What is this?

**Abstract interface** for all vector database providers.

## Why does it exist?

`NLPController` should not care if you use PGVector or Qdrant.

Both providers must implement the same methods.

## Required methods

| Method | Purpose |
|--------|---------|
| `connect()` / `disconnect()` | Open/close connection |
| `create_collection()` | Create vector collection/table |
| `delete_collection()` | Remove collection |
| `insert_many()` | Save vectors + text |
| `search_by_vector()` | Find similar documents |
| `get_collection_info()` | Stats about collection |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/vectordb/providers/PGVectorProvider.py` | PostgreSQL implementation |
| `src/stores/vectordb/providers/QdrantDBProvider.py` | Qdrant implementation |
| `src/stores/vectordb/VectorDBProviderFactory.py` | Creates implementations |
| `src/controllers/NLPController.py` | Calls interface methods |
| `src/models/db_schemes/minirag/schemes/datachunk.py` | `RetrievedDocument` return type |

## .NET comparison

```csharp
public interface IVectorStore {
    Task InsertManyAsync(...);
    Task<List<RetrievedDocument>> SearchAsync(...);
}
```
