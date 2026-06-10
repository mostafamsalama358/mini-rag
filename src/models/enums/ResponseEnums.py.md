# ResponseEnums.py

## What is this?

Enum with **API response signal strings**.

Every API returns a `"signal"` field so the client knows what happened.

## Why does it exist?

Same pattern as HTTP status codes, but as custom string messages.

Example response:

```json
{ "signal": "file_upload_success", "file_id": "123" }
```

## Main signals

| Signal | Meaning |
|--------|---------|
| `FILE_UPLOAD_SUCCESS` | File saved OK |
| `FILE_TYPE_NOT_SUPPORTED` | Wrong file type |
| `PROCESSING_SUCCESS` | Chunking task started/done |
| `INSERT_INTO_VECTORDB_SUCCESS` | Vectors saved OK |
| `VECTORDB_SEARCH_SUCCESS` | Search found results |
| `RAG_ANSWER_SUCCESS` | AI answer generated |
| `DATA_PUSH_TASK_READY` | Index task queued |

## Where is it used?

| File | How |
|------|-----|
| `src/models/__init__.py` | Exported as `ResponseSignal` |
| `src/routes/data.py` | Upload/process responses |
| `src/routes/nlp.py` | Search/answer responses |
| `src/controllers/DataController.py` | Validation messages |
| `src/tasks/file_processing.py` | Task success/failure signals |
| `src/tasks/data_indexing.py` | Index task signals |

## .NET comparison

Like custom result codes in `ApiResponse<T>` instead of only HTTP 200/400.
