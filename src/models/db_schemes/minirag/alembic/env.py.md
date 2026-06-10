# env.py

## What is this?

Alembic **migration runner** config for PostgreSQL.

Connects Alembic to your SQLAlchemy models.

## Why does it exist?

When you run `alembic upgrade head`, this file:

1. Reads DB URL from `alembic.ini`
2. Loads `SQLAlchemyBase.metadata` from schemes
3. Applies migration scripts in `versions/`

## Key line

```python
target_metadata = SQLAlchemyBase.metadata
```

This links models to auto-generated migrations.

## Where is it used?

| File | How |
|------|-----|
| `docker/minirag/entrypoint.sh` | Runs migrations on container start |
| `src/models/db_schemes/minirag/alembic/versions/*.py` | Migration scripts |
| `src/models/db_schemes/minirag/schemes/minirag_base.py` | Provides metadata |
| Root `README.md` | `alembic upgrade head` |

## .NET comparison

Like `DbContext` configuration in `dotnet ef` design-time factory.
