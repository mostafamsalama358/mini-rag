# LLMEnums.py

## What is this?

**Enum constants** for LLM providers and message roles.

## Why does it exist?

The app supports more than one AI provider (OpenAI, Cohere).

Enums avoid typos in string names like `"OPENAI"` vs `"openai"`.

## Main enums

| Enum | Purpose |
|------|---------|
| `LLMEnums` | Provider names: `OPENAI`, `COHERE` |
| `OpenAIEnums` | Roles: `system`, `user`, `assistant` |
| `CoHereEnums` | Cohere-specific roles and document types |
| `DocumentTypeEnum` | `document` vs `query` for embeddings |

## Where is it used?

| File | How |
|------|-----|
| `src/helpers/config.py` | `GENERATION_BACKEND`, `EMBEDDING_BACKEND` |
| `src/controllers/NLPController.py` | `DocumentTypeEnum` in embed/search |
| `src/stores/llm/LLMProviderFactory.py` | Picks provider* |
| `src/stores/llm/providers/OpenAIProvider.py` | Uses role enums* |
| `src/stores/llm/providers/CoHereProvider.py` | Uses Cohere enums* |

## .NET comparison

```csharp
public enum LlmProvider { OpenAI, Cohere }
public enum ChatRole { System, User, Assistant }
```
