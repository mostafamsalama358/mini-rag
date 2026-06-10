# __init__.py (providers - LLM)

## What is this?

Exports LLM provider classes from one place.

```python
from .CoHereProvider import CoHereProvider
from .OpenAIProvider import OpenAIProvider
```

## Why does it exist?

`LLMProviderFactory` can import both providers with:

```python
from .providers import OpenAIProvider, CoHereProvider
```

## Where is it used?

| File | How |
|------|-----|
| `src/stores/llm/LLMProviderFactory.py` | Creates provider instances |

## .NET comparison

Namespace export for DI registration of multiple implementations.
