# __init__.py

## What is this?

Empty package marker for `utils/`.

## Why does it exist?

Holds helper modules: `metrics.py`, `idempotency_manager.py`.

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | `from utils.metrics import setup_metrics` |
| `src/tasks/file_processing.py` | `from utils.idempotency_manager import IdempotencyManager` |

## .NET comparison

Like a `Common/` or `Shared/` utilities folder.
