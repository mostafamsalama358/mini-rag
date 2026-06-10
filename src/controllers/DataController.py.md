# DataController.py

## What is this?

Controller for **file upload** logic.

It checks files before they are saved to disk.

## Why does it exist?

The API must reject bad uploads:

- Wrong file type (only TXT and PDF allowed)
- File too large
- Bad file names (remove special characters)

## Main methods

| Method | What it does |
|--------|--------------|
| `validate_uploaded_file()` | Checks type and size |
| `generate_unique_filepath()` | Creates safe unique path per project |
| `get_clean_file_name()` | Removes bad characters from name |

## Where is it used?

| File | How |
|------|-----|
| `src/controllers/__init__.py` | Exported as `DataController` |
| `src/controllers/BaseController.py` | Parent class |
| `src/controllers/ProjectController.py` | Gets project folder path |
| `src/routes/data.py` | API endpoints call this |
| `src/models/enums/ResponseEnums.py` | Returns `ResponseSignal` messages* |
| `src/helpers/config.py` | `FILE_ALLOWED_TYPES`, `FILE_MAX_SIZE` |

## Flow (simple)

1. User uploads file via API
2. `DataController` validates it
3. File saved under `assets/files/{project_id}/`

## .NET comparison

Like a service class that validates `IFormFile` before saving to blob storage.
