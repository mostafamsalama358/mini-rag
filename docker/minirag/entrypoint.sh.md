# entrypoint.sh

## What is this?

A small **bash script** that runs when the Docker container starts.

It runs **before** the main app command (Uvicorn or Celery).

## Why does it exist?

The database tables must exist before the app works.

This script runs Alembic migrations:

```bash
alembic upgrade head
```

So PostgreSQL is ready when FastAPI starts.

## Where is it used?

| File | How |
|------|-----|
| `docker/minirag/Dockerfile` | Copied to `/entrypoint.sh` and set as `ENTRYPOINT` |
| `docker/docker-compose.yml` | Every service built from this Dockerfile runs this script first |
| `src/models/db_schemes/minirag/` | Alembic migrations live here |

## .NET comparison

Like running `dotnet ef database update` before `dotnet run` in Docker.
