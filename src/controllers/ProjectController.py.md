# ProjectController.py

## What is this?

Controller for **project folders** on disk.

Each project gets its own folder for uploaded files.

## Why does it exist?

Files are grouped by `project_id`.

This class creates and returns the folder path:

```
src/assets/files/{project_id}/
```

## Main method

```python
get_project_path(project_id: str)
```

- Builds the path
- Creates the folder if it does not exist
- Returns the full path

## Where is it used?

| File | How |
|------|-----|
| `src/controllers/DataController.py` | Saves uploads into project folder |
| `src/controllers/ProcessController.py` | Reads files from project folder |
| `src/controllers/__init__.py` | Exported |
| `src/controllers/BaseController.py` | Parent class |
| `src/models/ProjectModel.py` | Project also stored in PostgreSQL |

## .NET comparison

Like ensuring a directory exists per tenant or per project before saving files.
