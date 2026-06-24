# README.md (algorag db_schemes)

## What is this?

Short guide for running **Alembic database migrations** in this folder.

The existing `README.md` here has copy-paste commands.

## Why does it exist?

PostgreSQL tables (`projects`, `assets`, `chunks`, etc.) are created by migrations.

Developers need steps to:

1. Copy `alembic.ini.example` → `alembic.ini`
2. Set database URL
3. Run `alembic upgrade head`

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/algorag/alembic.ini.example` | Config template |
| `docker/algorag/entrypoint.sh` | Runs migrations in Docker |
| Root `README.md` | Points to Alembic step |
| `src/models/db_schemes/__init__.py` | Imports SQLAlchemy models defined here |

## Folder structure (expected)

```
algorag/
├── alembic/           # Migration scripts
├── schemes/           # SQLAlchemy models
├── alembic.ini.example
└── README.md
```

## .NET comparison

Like README next to your EF Core migrations folder explaining `dotnet ef database update`.
