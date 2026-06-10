# data_indexing.py

## What is this?

**Celery task** that pushes text chunks from PostgreSQL into the **vector database**.

Task name: `tasks.data_indexing.index_data_content`

## Why does it exist?

Chunking and vector indexing are separate steps.

This task embeds each chunk and stores vectors for semantic search.

## What the task does

1. Load project and connect to vector DB
2. Create collection (optional reset)
3. Read chunks page by page from DB
4. Call `NLPController.index_into_vector_db()` for each batch
5. Show progress with `tqdm`

## Where is it used?

| File | How |
|------|-----|
| `src/routes/nlp.py` | `index_data_content.delay(...)` |
| `src/tasks/process_workflow.py` | Second step after file processing |
| `src/celery_app.py` | Queue: `data_indexing` |
| `src/controllers/NLPController.py` | Embedding + insert logic |

## .NET comparison

Like a job that reads SQL rows and upserts into Azure AI Search index.
