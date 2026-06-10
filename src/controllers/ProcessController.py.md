# ProcessController.py

## What is this?

Controller for **reading and splitting** uploaded documents.

Turns PDF/TXT files into small **text chunks** for RAG.

## Why does it exist?

LLMs cannot read a whole book at once.

This class:

1. Loads file content (PDF or TXT)
2. Splits text into chunks
3. Returns chunks ready for the database

## Main methods

| Method | What it does |
|--------|--------------|
| `get_file_loader()` | Picks TextLoader or PyMuPDFLoader |
| `get_file_content()` | Reads full document |
| `process_file_content()` | Splits into chunks |
| `process_simpler_splitter()` | Simple split by new lines |

## File types supported

From `ProcessingEnum`:

- `.txt` — plain text
- `.pdf` — PDF via PyMuPDF

## Where is it used?

| File | How |
|------|-----|
| `src/controllers/__init__.py` | Exported |
| `src/controllers/ProjectController.py` | Gets file folder |
| `src/models/enums/ProcessingEnum.py` | File extension constants |
| `src/routes/data.py` | Process endpoint* |
| `src/tasks/file_processing.py` | Background processing* |
| `src/routes/schemes/data.py` | `ProcessRequest` body model |

## .NET comparison

Like a document parser service that chunks text before indexing in Elasticsearch.
