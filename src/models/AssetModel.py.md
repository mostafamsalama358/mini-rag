# AssetModel.py

## What is this?

**Data access** for the `Asset` table.

An **asset** is a file record linked to a project (name, type, path info).

## Why does it exist?

When a user uploads a file, the app saves:

1. The file on disk (`assets/files/`)
2. A row in PostgreSQL (`assets` table)

This class handles the database part.

## Main methods

| Method | What it does |
|--------|--------------|
| `create_asset()` | Insert new asset row |
| `get_all_project_assets()` | List assets by project and type |
| `get_asset_record()` | Find one asset by name |

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/__init__.py` | Uses `Asset` model |
| `src/models/enums/AssetTypeEnum.py` | Asset type = `"file"` |
| `src/routes/data.py` | Upload/list endpoints* |
| `src/tasks/file_processing.py` | Updates asset after processing* |

## .NET comparison

Like a repository for `FileMetadata` entities linked to a project.
