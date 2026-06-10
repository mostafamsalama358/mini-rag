# nlp.py

## What is this?

FastAPI **router** for NLP and RAG endpoints.

Prefix: `/api/v1/nlp`

## Why does it exist?

After files are chunked, users need to:

1. Push chunks into the vector database
2. Search similar text
3. Ask questions and get AI answers (RAG)

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/index/push/{project_id}` | Index chunks to vector DB (Celery) |
| GET | `/index/info/{project_id}` | Collection info |
| POST | `/index/search/{project_id}` | Semantic search |
| POST | `/index/answer/{project_id}` | Full RAG answer |

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | `app.include_router(nlp.nlp_router)` |
| `src/controllers/NLPController.py` | Search and RAG logic |
| `src/routes/schemes/nlp.py` | `PushRequest`, `SearchRequest` |
| `src/tasks/data_indexing.py` | Background indexing task |
| `src/models/ProjectModel.py` | Load project |
| `src/assets/mini-rag-app.postman_collection.json` | API tests |

## .NET comparison

Like `SearchController` + `ChatController` for vector search and Q&A.
