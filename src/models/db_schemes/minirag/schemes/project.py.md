# project.py

## What is this?

SQLAlchemy **entity** for the `projects` table.

A **project** is one RAG workspace (one set of documents and chunks).

## Why does it exist?

Every upload and chunk belongs to a project.

This class maps to PostgreSQL table `projects`.

## Main columns

| Column | Meaning |
|--------|---------|
| `project_id` | Primary key (integer) |
| `project_uuid` | Unique UUID |
| `created_at` / `updated_at` | Timestamps |

## Relationships

- `chunks` → many `DataChunk` rows
- `assets` → many `Asset` rows

## Where is it used?

| File | How |
|------|-----|
| `src/models/ProjectModel.py` | CRUD operations |
| `src/models/db_schemes/__init__.py` | Exported |
| `src/routes/data.py`, `src/routes/nlp.py` | All endpoints use project_id |
| `src/controllers/NLPController.py` | Vector collection per project |
| Alembic migration `fee4cd54bd38` | Creates this table |

## .NET comparison

```csharp
public class Project {
    public int ProjectId { get; set; }
    public Guid ProjectUuid { get; set; }
    public ICollection<DataChunk> Chunks { get; set; }
}
```
