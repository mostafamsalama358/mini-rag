# nlp.py (schemes)

## What is this?

**Pydantic models** for NLP/RAG API request bodies.

## Why does it exist?

Search and push-to-vector-db endpoints need typed input.

## Classes

### PushRequest

Push chunks into the vector database.

| Field | Default | Meaning |
|-------|---------|---------|
| `do_reset` | 0 | Delete old collection first? |

### SearchRequest

Semantic search in project documents.

| Field | Default | Meaning |
|-------|---------|---------|
| `text` | required | Query text |
| `limit` | 5 | Max results |

## Where is it used?

| File | How |
|------|-----|
| `src/routes/nlp.py` | Endpoint bodies |
| `src/controllers/NLPController.py` | Uses same data in methods |
| `src/assets/mini-rag-app.postman_collection.json` | API examples |

## .NET comparison

```csharp
public record SearchRequest(string Text, int Limit = 5);
```
