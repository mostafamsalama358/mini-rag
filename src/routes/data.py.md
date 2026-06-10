# data.py

## What is this?

FastAPI **router** for file upload and processing endpoints.

Prefix: `/api/v1/data`

In .NET this is like a **Controller** with `[Route("api/v1/data")]`.

## Why does it exist?

Users need HTTP endpoints to:

1. Upload PDF/TXT files
2. Process files into text chunks (background job)
3. Process + push to vector DB in one workflow

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/upload/{project_id}` | Save uploaded file |
| POST | `/process/{project_id}` | Start chunking task (Celery) |
| POST | `/process-and-push/{project_id}` | Process then index (Celery chain) |

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | `app.include_router(data.data_router)` |
| `src/controllers/DataController.py` | Validates and saves files |
| `src/controllers/ProjectController.py` | Project folder path |
| `src/routes/schemes/data.py` | `ProcessRequest` body |
| `src/tasks/file_processing.py` | Background process task |
| `src/tasks/process_workflow.py` | Combined workflow |
| `src/models/ProjectModel.py` | Get or create project |
| `src/models/AssetModel.py` | Save file metadata |
| `src/assets/mini-rag-app.postman_collection.json` | API tests |

## .NET comparison

Like `FilesController` with upload + enqueue background job endpoints.
