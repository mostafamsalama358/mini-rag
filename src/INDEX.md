# Mini-RAG — src folder map

Simple guide for **.NET developers** learning this Python project.

## What is `src/`?

The main application code. Like the `WebApi/` project in a .NET solution.

## How data flows (simple)

```
HTTP Request
    ↓
routes/          ← API endpoints (like Controllers)
    ↓
controllers/     ← Business logic (like Services)
    ↓
models/          ← Database access (like Repositories)
    ↓
PostgreSQL + Vector DB
```

Background jobs use **Celery**:

```
celery_app.py → tasks/ → controllers/ → models/
```

## Folder guide

| Folder | Role | .NET similar |
|--------|------|--------------|
| `main.py` | App entry | `Program.cs` |
| `helpers/` | Config | `appsettings` + Options |
| `routes/` | HTTP routes | Controllers |
| `controllers/` | Logic | Services |
| `models/` | DB layer | Repositories + Entities |
| `stores/` | AI + Vector APIs | HttpClient wrappers |
| `tasks/` | Background jobs | Hangfire jobs |
| `utils/` | Helpers | Shared utilities |
| `assets/` | Uploads + Postman | `wwwroot` + test files |

## Full API flow (RAG)

```
1. POST /api/v1/data/upload/{project_id}     → save file
2. POST /api/v1/data/process/{project_id}    → chunks (Celery)
3. POST /api/v1/nlp/index/push/{project_id}  → vectors (Celery)
4. POST /api/v1/nlp/index/answer/{project_id}  → RAG answer
```

Or use one call: `POST /api/v1/data/process-and-push/{project_id}`

## Each file has a `.md` doc

Open `SomeFile.py.md` next to `SomeFile.py` for details.

## Start here

1. `main.py.md` — how the app starts
2. `helpers/config.py.md` — all settings
3. `routes/data.py.md` + `routes/nlp.py.md` — all API endpoints
4. `controllers/NLPController.py.md` — RAG core logic
5. `tasks/file_processing.py.md` — background processing
6. `stores/llm/LLMProviderFactory.py.md` — AI providers
7. `stores/vectordb/VectorDBProviderFactory.py.md` — vector DB

## Restored files (now complete)

All source files are restored from Git branch `tut-017`:

- `routes/data.py`, `routes/nlp.py`
- `stores/llm/*`, `stores/vectordb/*`
- `tasks/*`, `utils/*`
- `models/db_schemes/minirag/schemes/*`
- Alembic migrations

Each restored file now has its own `.md` documentation.
