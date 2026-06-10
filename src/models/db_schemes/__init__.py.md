# __init__.py

## What is this?

Re-exports **SQLAlchemy database models** (table classes).

One import point for all DB entity types.

## Why does it exist?

Other files import like this:

```python
from models.db_schemes import Project, DataChunk, Asset
```

## What it should export

From `models/db_schemes/minirag/schemes/`:

| Class | Table purpose |
|-------|---------------|
| `Project` | One RAG project |
| `DataChunk` | Text chunk from a document |
| `Asset` | Uploaded file metadata |
| `RetrievedDocument` | Search result shape |

## Where is it used?

| File | How |
|------|-----|
| `src/models/ProjectModel.py` | Uses `Project` |
| `src/models/AssetModel.py` | Uses `Asset` |
| `src/models/ChunkModel.py` | Uses `DataChunk` |
| `src/controllers/NLPController.py` | Uses `Project`, `DataChunk` |

## Scheme files location

Entity classes live in `minirag/schemes/`:

- `project.py`, `asset.py`, `datachunk.py`, `celery_task_execution.py`

Each has its own `.md` doc file.

## .NET comparison

Like `using MyApp.Entities;` for all EF Core entity classes.
