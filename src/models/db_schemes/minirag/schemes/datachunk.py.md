# datachunk.py

## What is this?

SQLAlchemy entity for `chunks` table + Pydantic model for search results.

## Why does it exist?

After splitting a document, each piece is a **DataChunk** row.

Chunks are later embedded and sent to the vector DB.

## DataChunk columns

| Column | Meaning |
|--------|---------|
| `chunk_text` | Text content |
| `chunk_metadata` | JSON metadata |
| `chunk_order` | Order in document |
| `chunk_project_id` | Links to project |
| `chunk_asset_id` | Links to source file |

## RetrievedDocument

Simple Pydantic model for search results:

```python
class RetrievedDocument(BaseModel):
    text: str
    score: float
```

## Where is it used?

| File | How |
|------|-----|
| `src/models/ChunkModel.py` | Insert/query chunks |
| `src/tasks/file_processing.py` | Saves new chunks |
| `src/tasks/data_indexing.py` | Reads chunks for indexing |
| `src/controllers/NLPController.py` | Index and search |
| `src/stores/vectordb/VectorDBInterface.py` | Returns `List[RetrievedDocument]` |

## .NET comparison

`DataChunk` = document segment entity; `RetrievedDocument` = search hit DTO.
