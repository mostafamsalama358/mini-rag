# __init__.py (providers - VectorDB)

## What is this?

Exports vector DB provider classes.

```python
from .QdrantDBProvider import QdrantDBProvider
from .PGVectorProvider import PGVectorProvider
```

## Why does it exist?

`VectorDBProviderFactory` imports both from here.

## Where is it used?

| File | How |
|------|-----|
| `src/stores/vectordb/VectorDBProviderFactory.py` | Creates PGVector or Qdrant client |

## .NET comparison

Export point for vector store implementations.
