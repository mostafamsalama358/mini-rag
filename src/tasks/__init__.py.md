# __init__.py

## What is this?

Empty package marker for `tasks/`.

## Why does it exist?

Celery loads task modules by string path:

```python
"tasks.file_processing"
"tasks.data_indexing"
```

This folder must be a Python package.

## Where is it used?

| File | How |
|------|-----|
| `src/celery_app.py` | `include=[ "tasks.file_processing", ... ]` |

## .NET comparison

Folder for background job classes in your worker project.
