# rag.py (English)

## What is this?

**English RAG prompt templates** for the LLM.

Uses Python `string.Template` with placeholders like `$query` and `$chunk_text`.

## Why does it exist?

`NLPController.answer_rag_question()` needs three prompt parts:

| Template | Role |
|----------|------|
| `system_prompt` | Tells LLM it is a helpful assistant |
| `document_prompt` | One retrieved chunk (`$doc_num`, `$chunk_text`) |
| `footer_prompt` | User question (`$query`) |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/llm/templates/template_parser.py` | Loads this when language is `en` |
| `src/controllers/NLPController.py` | Builds full RAG prompt |
| `src/helpers/config.py` | `DEFAULT_LANG = "en"` fallback |

## .NET comparison

Like a prompt template file in English for your AI chat feature.
