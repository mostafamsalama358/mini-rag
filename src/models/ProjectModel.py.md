# ProjectModel.py

## What is this?

**Data access** for the `Project` table in PostgreSQL.

Like a **repository** for projects in .NET.

## Why does it exist?

Projects are the top-level container for files and chunks.

This class reads and writes project rows in the database.

## Main methods

| Method | What it does |
|--------|--------------|
| `create_project()` | Insert new project |
| `get_project_or_create_one()` | Find by ID or create |
| `get_all_projects()` | Paginated list |

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/__init__.py` | Uses `Project` SQLAlchemy model |
| `src/models/BaseDataModel.py` | Parent class |
| `src/controllers/NLPController.py` | Needs `Project` for vector ops |
| `src/routes/data.py` | Project API endpoints* |
| `src/routes/nlp.py` | RAG needs project* |

## Database table

Defined in `models/db_schemes/minirag/schemes/project.py`*.

## .NET comparison

```csharp
public class ProjectRepository {
    Task<Project> GetOrCreateAsync(string projectId);
}
```
