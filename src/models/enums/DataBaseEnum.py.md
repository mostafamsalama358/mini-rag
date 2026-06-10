# DataBaseEnum.py

## What is this?

Enum with **MongoDB collection names** from an older version of the project.

## Why does it exist?

When the app used MongoDB, tables were called "collections".

These names were used in Motor/PyMongo code.

## Values

| Name | Value |
|------|-------|
| `COLLECTION_PROJECT_NAME` | `"projects"` |
| `COLLECTION_CHUNK_NAME` | `"chunks"` |
| `COLLECTION_ASSET_NAME` | `"assets"` |

## Where is it used?

| File | How |
|------|-----|
| `src/models/ProjectModel.py` | Imported but may be unused now |
| `src/models/AssetModel.py` | Imported but may be unused now |
| `src/models/ChunkModel.py` | Imported but may be unused now |

## Current status

The app moved to **PostgreSQL**. These collection names are **legacy**.

SQLAlchemy models in `db_schemes/minirag/schemes/` replace Mongo collections.

## .NET comparison

Old NoSQL table names — like constants before you migrated to Entity Framework.
