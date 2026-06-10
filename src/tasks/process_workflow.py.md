# process_workflow.py

## What is this?

**Celery workflow** that chains two tasks: process file → index vectors.

## Why does it exist?

Users often want both steps in one API call.

Instead of calling process then push manually, this runs them in order.

## Tasks

| Task | What it does |
|------|--------------|
| `process_and_push_workflow` | Starts the chain, returns workflow ID |
| `push_after_process_task` | Runs indexing after process finishes |

Uses Celery `chain()`:

```
process_project_files → push_after_process_task
```

## Where is it used?

| File | How |
|------|-----|
| `src/routes/data.py` | `/process-and-push/{project_id}` endpoint |
| `src/tasks/file_processing.py` | First task in chain |
| `src/tasks/data_indexing.py` | `_index_data_content` called in second task |
| `src/celery_app.py` | Route to `file_processing` queue |

## .NET comparison

Like chaining two Hangfire jobs: `ContinueJobWith` process then index.
