# ChunkModel.py

## What is this?

**Data access** for the `DataChunk` table.

A **chunk** is a small piece of text from an uploaded document.

## Why does it exist?

After splitting a PDF/TXT, each piece is saved as a row.

Later these chunks are embedded and sent to the vector database.

## Main methods

| Method | What it does |
|--------|--------------|
| `create_chunk()` | Insert one chunk |
| `insert_many_chunks()` | Bulk insert (batches of 100) |
| `get_chunk()` | Find by chunk ID |
| `delete_chunks_by_project_id()` | Delete all chunks for a project |
| `get_poject_chunks()` | Paginated list |
| `get_total_chunks_count()` | Count chunks |

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/__init__.py` | Uses `DataChunk` model |
| `src/controllers/NLPController.py` | Indexes chunks into vector DB |
| `src/controllers/ProcessController.py` | Creates chunks from files |
| `src/routes/data.py` | Process/push endpoints* |
| `src/tasks/data_indexing.py` | Background indexing* |

## Legacy note

This file still imports `bson` and `pymongo` from the old MongoDB version.

The app now uses PostgreSQL + SQLAlchemy. Those Mongo imports may be unused.

## .NET comparison

Like storing document segments in SQL before sending them to a vector index.
