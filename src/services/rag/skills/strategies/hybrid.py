"""Hybrid retrieval — BM25+dense when port provided, else vector fallback."""

from __future__ import annotations

from typing import Any


class HybridRetrievalStrategy:
    name = "hybrid"

    async def retrieve(self, *, ctx: Any, **kwargs: Any) -> tuple[list, str]:
        hybrid_search = kwargs.get("hybrid_search")
        if hybrid_search is not None:
            docs = await hybrid_search()
            if docs is False:
                docs = []
            return list(docs or []), "hybrid"
        search = kwargs["search_vector"]
        docs = await search()
        if docs is False:
            docs = []
        return list(docs or []), "hybrid_fallback→vector"
