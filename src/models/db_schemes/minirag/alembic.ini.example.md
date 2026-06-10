# alembic.ini.example

## What is this?

Example Alembic config for **local development** (outside Docker).

Same role as `docker/minirag/alembic.example.ini`.

## Why does it exist?

When you run migrations on your machine:

```bash
cd src/models/db_schemes/minirag
cp alembic.ini.example alembic.ini
alembic upgrade head
```

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/minirag/README.md` | Setup instructions |
| `docker/minirag/entrypoint.sh` | Docker uses `alembic.ini` (not this example) |
| `docker/minirag/Dockerfile` | Copies `alembic.ini` into container |
| Root `README.md` | `alembic upgrade head` step |

## Difference from Docker version

Local file uses `localhost` for PostgreSQL.

Docker version uses `pgvector` as host name.

## .NET comparison

Like `dotnet ef` connection string in `appsettings.json` for migrations.
