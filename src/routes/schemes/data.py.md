# data.py (schemes)

## What is this?

**Pydantic models** for data/upload API request bodies.

Pydantic is like **DTOs** or **request models** in .NET.

## Why does it exist?

FastAPI validates JSON input against these classes.

Wrong data = automatic 422 error response.

## Classes

### ProcessRequest

Used when processing an uploaded file into chunks.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `file_id` | str | — | Which file to process |
| `chunk_size` | int | 100 | Chunk text size |
| `overlap_size` | int | 20 | Overlap between chunks |
| `do_reset` | int | 0 | Reset existing chunks? |

## Where is it used?

| File | How |
|------|-----|
| `src/routes/data.py` | Endpoint parameter type |
| `src/controllers/ProcessController.py` | Business logic uses same values |
| `src/assets/mini-rag-app.postman_collection.json` | Example API calls |

## Note

This is in `routes/schemes/` — **not** the route file itself.

The actual routes live in `src/routes/data.py`.

## .NET comparison

```csharp
public record ProcessRequest(string FileId, int ChunkSize = 100);
```
