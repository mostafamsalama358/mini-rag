# NLPController.py

## What is this?

Controller for **AI and vector search** — the core of RAG.

RAG = **R**etrieval **A**ugmented **G**eneration (search docs, then ask LLM).

## Why does it exist?

This class connects:

- Vector database (find similar text)
- Embedding model (turn text into numbers)
- LLM (generate the answer)
- Prompt templates (how to ask the LLM)

## Main methods

| Method | What it does |
|--------|--------------|
| `create_collection_name()` | Name for vector collection per project |
| `index_into_vector_db()` | Save chunks as vectors |
| `search_vector_db_collection()` | Semantic search |
| `answer_rag_question()` | Full RAG: search + LLM answer |
| `reset_vector_db_collection()` | Delete collection |
| `get_vector_db_collection_info()` | Collection stats |

## Where is it used?

| File | How |
|------|-----|
| `src/controllers/__init__.py` | Exported |
| `src/main.py` | Gets LLM and vector clients on startup |
| `src/models/db_schemes/` | Uses `Project`, `DataChunk` |
| `src/stores/llm/LLMEnums.py` | `DocumentTypeEnum` for embeddings |
| `src/stores/llm/templates/` | RAG prompt templates* |
| `src/routes/nlp.py` | Search and answer endpoints* |
| `src/tasks/data_indexing.py` | Index chunks in background* |

## RAG flow (simple)

1. User asks a question
2. Embed the question → vector
3. Search similar chunks in vector DB
4. Build prompt with found chunks
5. LLM generates answer

## .NET comparison

Like a service that queries Azure AI Search then calls OpenAI Chat Completions.
