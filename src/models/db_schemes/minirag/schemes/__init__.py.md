# __init__.py (schemes)

## What is this?

Exports all **SQLAlchemy entity classes** from the schemes package.

## Why does it exist?

One import for Alembic and other code:

```python
from schemes import Project, Asset, DataChunk, SQLAlchemyBase
```

## What it exports

| Name | From file |
|------|-----------|
| `SQLAlchemyBase` | `minirag_base.py` |
| `Project` | `project.py` |
| `Asset` | `asset.py` |
| `DataChunk`, `RetrievedDocument` | `datachunk.py` |
| `CeleryTaskExecution` | `celery_task_execution.py` |

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/__init__.py` | Re-exports for app code |
| `src/models/db_schemes/minirag/alembic/env.py` | Migration metadata |

## .NET comparison

Barrel export of all entity types in one namespace.
