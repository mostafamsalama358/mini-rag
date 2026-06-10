# asset.py

## What is this?

SQLAlchemy **entity** for the `assets` table.

An **asset** is metadata about an uploaded file.

## Why does it exist?

When a user uploads a file, the app saves:

- File on disk (`assets/files/`)
- Row in `assets` table (name, size, type, project link)

## Main columns

| Column | Meaning |
|--------|---------|
| `asset_id` | Primary key |
| `asset_name` | Stored file name on disk |
| `asset_type` | Usually `"file"` |
| `asset_size` | Size in bytes |
| `asset_project_id` | Foreign key to `projects` |

## Where is it used?

| File | How |
|------|-----|
| `src/models/AssetModel.py` | Insert and query assets |
| `src/routes/data.py` | Creates asset after upload |
| `src/tasks/file_processing.py` | Finds files to process |
| `src/models/enums/AssetTypeEnum.py` | `FILE` type constant |

## .NET comparison

Entity for `FileMetadata` linked to a project.
