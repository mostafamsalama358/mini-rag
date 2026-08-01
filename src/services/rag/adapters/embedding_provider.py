"""Embedding client → IEmbeddingProvider adapter (spec 015)."""

from __future__ import annotations

import asyncio
from typing import Any

from stores.llm.LLMEnums import DocumentTypeEnum


class EmbeddingProviderAdapter:
    """Wraps embedding_client.embed_text[_async] behind IEmbeddingProvider."""

    def __init__(self, embedding_client: Any) -> None:
        self._client = embedding_client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embed_async = getattr(self._client, "embed_text_async", None)
        if embed_async is not None:
            raw = await embed_async(
                text=texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )
        else:
            raw = await asyncio.to_thread(
                self._client.embed_text,
                text=texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )

        if not raw:
            return [[] for _ in texts]

        if (
            len(texts) == 1
            and isinstance(raw, list)
            and raw
            and isinstance(raw[0], (int, float))
        ):
            return [[float(x) for x in raw]]

        vectors: list[list[float]] = []
        for item in raw:
            if isinstance(item, list) and item and isinstance(item[0], (int, float)):
                vectors.append([float(x) for x in item])
            else:
                vectors.append([])
        while len(vectors) < len(texts):
            vectors.append([])
        return vectors[: len(texts)]
