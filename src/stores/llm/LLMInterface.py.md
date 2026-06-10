# LLMInterface.py

## What is this?

**Abstract base class** (interface) for all LLM providers.

In .NET this is like `ILLMService` or `IGenerativeAIClient`.

## Why does it exist?

OpenAI and Cohere have different SDKs.

The rest of the app talks to **LLMInterface** only.

You can swap providers without changing controllers.

## Methods every provider must implement

| Method | Purpose |
|--------|---------|
| `set_generation_model()` | Pick chat model |
| `set_embedding_model()` | Pick embedding model |
| `generate_text()` | Ask LLM for answer |
| `embed_text()` | Turn text into vector |
| `construct_prompt()` | Build chat message object |

## Where is it used?

| File | How |
|------|-----|
| `src/stores/llm/LLMProviderFactory.py` | Creates concrete providers* |
| `src/stores/llm/providers/OpenAIProvider.py` | Implements interface* |
| `src/stores/llm/providers/CoHereProvider.py` | Implements interface* |
| `src/controllers/NLPController.py` | Calls `generate_text`, `embed_text` |
| `src/main.py` | Creates clients on startup |

## .NET comparison

```csharp
public interface ILlmClient {
    Task<string> GenerateTextAsync(string prompt);
    Task<float[]> EmbedTextAsync(string text);
}
```
