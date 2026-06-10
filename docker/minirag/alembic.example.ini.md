# alembic.example.ini

## What is this?

An **example config file** for Alembic (database migrations).

Alembic is like **Entity Framework Migrations** in .NET.

## Why does it exist?

You must copy it to a real `alembic.ini` with your database URL.

It tells Alembic:

- Where migration scripts are (`alembic/` folder)
- How to connect to PostgreSQL (`sqlalchemy.url`)

## How to use it

```bash
cd docker/minirag
cp alembic.example.ini alembic.ini
# Edit alembic.ini with your password
```

Also see `src/models/db_schemes/minirag/alembic.ini.example` for local dev.

## Where is it used?

| File | How |
|------|-----|
| `docker/minirag/Dockerfile` | Expects `alembic.ini` at build time (you create it from this example) |
| `docker/minirag/entrypoint.sh` | Runs `alembic upgrade head` using this config |
| `docker/.gitignore` | Real `alembic.ini` is not committed (has secrets) |
| `docker/README.md` | Setup steps mention copying this file |

## Important setting

```
sqlalchemy.url = postgresql://postgres:postgres_password@pgvector:5432/minirag
```

`pgvector` is the Docker service name (not `localhost` inside Docker).
