# BaseController.py

## What is this?

**Base class** for all controllers in this project.

In .NET this is like a **base controller** with shared helpers.

## Why does it exist?

All controllers need the same things:

- App settings from config
- Paths to store uploaded files
- Path for local database files
- A helper to generate random file names

Child classes call `super().__init__()` to get this for free.

## What it provides

| Method / property | Purpose |
|-------------------|---------|
| `app_settings` | Config from `helpers/config.py` |
| `files_dir` | `src/assets/files/` — uploaded files |
| `database_dir` | `src/assets/database/` — local DB files |
| `generate_random_string()` | Random name for new files |
| `get_database_path()` | Creates folder if missing |

## Where is it used?

| File | Extends BaseController |
|------|------------------------|
| `src/controllers/DataController.py` | Yes — file upload validation |
| `src/controllers/ProjectController.py` | Yes — project folders |
| `src/controllers/ProcessController.py` | Yes — read and split files |
| `src/controllers/NLPController.py` | Yes — RAG and vector search |

## .NET comparison

```csharp
public abstract class BaseController : ControllerBase {
    protected Settings _settings;
    protected string FilesDir => "...";
}
```
