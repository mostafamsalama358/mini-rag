# file_processing.py

## What is this?

**Celery background task** that reads files and saves text chunks to PostgreSQL.

Task name: `tasks.file_processing.process_project_files`

## Why does it exist?

Processing PDF/TXT is slow. The API returns immediately with a `task_id`.

The worker does the heavy work in the background.

## What the task does

1. Check idempotency (no duplicate run)
2. Load project and file assets
3. Read file with `ProcessController`
4. Split into chunks
5. Save chunks to `chunks` table
6. Optional: reset old chunks and vector collection

## Where is it used?

| File | How |
|------|-----|
| `src/routes/data.py` | `process_project_files.delay(...)` |
| `src/celery_app.py` | Registered in `include` and `task_routes` |
| `src/tasks/process_workflow.py` | First step in chain |
| `src/controllers/ProcessController.py` | Read and split files |
| `src/utils/idempotency_manager.py` | Duplicate protection |

## .NET comparison

Background job like Hangfire `ProcessFileJob(projectId, fileId)`.
