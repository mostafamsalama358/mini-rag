# CoHereProvider.py

## What is this?

**Cohere implementation** of `LLMInterface`.

Uses Cohere API for chat and embeddings.

## Why does it exist?

Cohere is often used for **embeddings** (multilingual models).

The project can use OpenAI for answers and Cohere for vectors.

## Main methods

| Method | Notes |
|--------|-------|
| `generate_text()` | Cohere `chat()` API |
| `embed_text()` | Uses `DOCUMENT` vs `QUERY` input type |
| `construct_prompt()` | Builds `{role, text}` (Cohere format) |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/llm/LLMProviderFactory.py` | Creates when provider is COHERE |
| `src/stores/llm/LLMEnums.py` | `CoHereEnums`, `DocumentTypeEnum` |
| `src/controllers/NLPController.py` | Embedding for search and index |
| `src/helpers/config.py` | `COHERE_API_KEY`, `EMBEDDING_MODEL_ID` |

## .NET comparison

Like a dedicated `ICohereEmbeddingService` wrapping the Cohere SDK.
