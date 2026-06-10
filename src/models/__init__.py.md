# __init__.py

## What is this?

Package init for `models` folder.

Exports common **enums** used across the app.

## Why does it exist?

Short imports:

```python
from models import ResponseSignal, ProcessingEnum
```

## What it exports

| Name | From |
|------|------|
| `ResponseSignal` | `enums/ResponseEnums.py` |
| `ProcessingEnum` | `enums/ProcessingEnum.py` |

## Where is it used?

| File | How |
|------|-----|
| `src/controllers/DataController.py` | `ResponseSignal` for upload messages |
| `src/controllers/ProcessController.py` | `ProcessingEnum` for file types |
| `src/routes/data.py`, `src/routes/nlp.py` | API response signals |
| `src/tasks/*.py` | Task success/failure signals |

## .NET comparison

Like a namespace that re-exports shared enums.
