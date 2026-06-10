# script.py.mako

## What is this?

**Mako template** for new Alembic migration files.

When you run `alembic revision`, Alembic copies this template.

## Why does it exist?

Every new migration needs the same structure:

- `revision` ID
- `down_revision` (previous migration)
- `upgrade()` function
- `downgrade()` function

This template generates that boilerplate.

## Where is it used?

| File | How |
|------|-----|
| Alembic CLI | `alembic revision --autogenerate -m "message"` |
| `src/models/db_schemes/minirag/alembic/versions/*.py` | Files created from this template |

## .NET comparison

Like the default scaffold template for `dotnet ef migrations add`.
