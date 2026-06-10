# LLMProviderFactory.py

## What is this?

**Factory** that creates the correct LLM provider (OpenAI or Cohere).

In .NET this is like a factory that returns `IOpenAIService` or `ICohereService`.

## Why does it exist?

The app can use different AI backends for:

- **Generation** (chat answers) — often OpenAI
- **Embeddings** (vectors) — often Cohere

One factory hides the choice from `main.py` and `celery_app.py`.

## How it works

```python
factory = LLMProviderFactory(settings)
client = factory.create(provider=settings.GENERATION_BACKEND)
```

| Provider string | Returns |
|-----------------|---------|
| `"OPENAI"` | `OpenAIProvider` |
| `"COHERE"` | `CoHereProvider` |

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | Creates generation + embedding clients on startup |
| `src/celery_app.py` | Same in `get_setup_utils()` |
| `src/stores/llm/providers/OpenAIProvider.py` | OpenAI implementation |
| `src/stores/llm/providers/CoHereProvider.py` | Cohere implementation |
| `src/helpers/config.py` | `GENERATION_BACKEND`, `EMBEDDING_BACKEND` |

## .NET comparison

```csharp
public ILlmClient Create(string provider) =>
    provider switch {
        "OPENAI" => new OpenAiClient(...),
        "COHERE" => new CohereClient(...),
    };
```
