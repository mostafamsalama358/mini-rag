# template_parser.py

## What is this?

Loads **RAG prompt templates** by language (English or Arabic).

## Why does it exist?

RAG prompts must tell the LLM how to use retrieved documents.

Templates live in `locales/en/rag.py` and `locales/ar/rag.py`.

This class picks the right language and fills in variables.

## Main method

```python
template_parser.get("rag", "system_prompt")
template_parser.get("rag", "document_prompt", {"doc_num": 1, "chunk_text": "..."})
```

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | Creates parser with `PRIMARY_LANG` |
| `src/celery_app.py` | Same in workers |
| `src/controllers/NLPController.py` | Builds RAG prompt in `answer_rag_question()` |
| `src/stores/llm/templates/locales/en/rag.py` | English prompts |
| `src/stores/llm/templates/locales/ar/rag.py` | Arabic prompts |
| `src/helpers/config.py` | `PRIMARY_LANG`, `DEFAULT_LANG` |

## .NET comparison

Like loading localized `.resx` or JSON prompt templates by culture.
