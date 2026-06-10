# minirag_base.py

## What is this?

Creates the SQLAlchemy **Base class** for all database tables.

One line of code — very important.

```python
SQLAlchemyBase = declarative_base()
```

## Why does it exist?

All entity classes (`Project`, `Asset`, `DataChunk`) inherit from this base.

Alembic uses `SQLAlchemyBase.metadata` to generate migrations.

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/minirag/schemes/project.py` | `class Project(SQLAlchemyBase)` |
| `src/models/db_schemes/minirag/schemes/asset.py` | `class Asset(SQLAlchemyBase)` |
| `src/models/db_schemes/minirag/schemes/datachunk.py` | `class DataChunk(SQLAlchemyBase)` |
| `src/models/db_schemes/minirag/schemes/celery_task_execution.py` | Task tracking table |
| `src/models/db_schemes/minirag/alembic/env.py` | `target_metadata = SQLAlchemyBase.metadata` |

## .NET comparison

Like `DbContext` base or `[Table]` entity base in Entity Framework.
