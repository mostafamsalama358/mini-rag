# fee4cd54bd38_initial_commit.py

## What is this?

First Alembic **migration** — creates core database tables.

## Why does it exist?

PostgreSQL needs tables before the app can save data.

This migration creates:

| Table | Purpose |
|-------|---------|
| `projects` | RAG projects |
| `assets` | Uploaded files |
| `chunks` | Text chunks |

## Revision info

- **Revision ID:** `fee4cd54bd38`
- **Parent:** none (first migration)

## Where is it used?

| File | How |
|------|-----|
| `alembic/env.py` | Applied by `alembic upgrade head` |
| `docker/minirag/entrypoint.sh` | Runs on Docker start |
| Entity files in `schemes/` | Match these table definitions |

## .NET comparison

Initial EF migration `CreateProjectsAssetsChunks`.
