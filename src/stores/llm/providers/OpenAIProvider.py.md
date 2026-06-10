# OpenAIProvider.py

## What is this?

**OpenAI implementation** of `LLMInterface`.

Talks to OpenAI API for chat and embeddings.

## Why does it exist?

When `GENERATION_BACKEND` or `EMBEDDING_BACKEND` is `"OPENAI"`, this class is used.

## Main methods

| Method | API used |
|--------|----------|
| `generate_text()` | Chat Completions (`gpt-4o-mini`, etc.) |
| `embed_text()` | Embeddings API |
| `construct_prompt()` | Builds `{role, content}` message |
| `process_text()` | Trims text to max characters |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/llm/LLMProviderFactory.py` | Creates this when provider is OPENAI |
| `src/stores/llm/LLMInterface.py` | Implements this interface |
| `src/controllers/NLPController.py` | Calls `generate_text`, `embed_text` |
| `src/helpers/config.py` | `OPENAI_API_KEY`, `OPENAI_API_URL`, model IDs |

## .NET comparison

Wrapper around `OpenAIClient` SDK — like an `IOpenAIService` implementation.
