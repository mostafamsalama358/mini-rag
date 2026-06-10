# __init__.py

## What is this?

Makes the `controllers` folder a Python **package**.

Also **exports** all controller classes in one place.

## Why does it exist?

Other files can import like this:

```python
from controllers import DataController, NLPController
```

Instead of long paths for each file.

## What it exports

| Name | From file |
|------|-----------|
| `DataController` | `DataController.py` |
| `ProjectController` | `ProjectController.py` |
| `ProcessController` | `ProcessController.py` |
| `NLPController` | `NLPController.py` |

## Where is it used?

| File | How |
|------|-----|
| `src/routes/data.py` | Imports controllers for API* |
| `src/routes/nlp.py` | Imports `NLPController`* |
| `src/tasks/*.py` | Background tasks use controllers* |

## .NET comparison

Like putting several services in one namespace so you can `using Controllers;`.
