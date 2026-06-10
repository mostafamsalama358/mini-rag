# rag.py (Arabic)

## What is this?

**Arabic RAG prompt templates** for the LLM.

Same structure as English `rag.py`, but text is in Arabic.

## Why does it exist?

When `PRIMARY_LANG = "ar"`, the app uses these prompts.

The LLM is told to answer in the same language as the user question.

## Templates

| Name | Arabic purpose |
|------|----------------|
| `system_prompt` | Assistant rules in Arabic |
| `document_prompt` | Document chunk format |
| `footer_prompt` | Question + answer section |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/llm/templates/template_parser.py` | Loads when language is `ar` |
| `src/controllers/NLPController.py` | RAG answer flow |
| `src/.env.example` | Example: `PRIMARY_LANG = "ar"` |

## .NET comparison

Localized Arabic resource file for the same prompts as English.
