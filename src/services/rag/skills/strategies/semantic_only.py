"""Semantic-only retrieval — distinct from default vector path."""

from __future__ import annotations

import inspect
from typing import Any


class SemanticOnlyRetrievalStrategy:
    name = "semantic_only"

    async def retrieve(self, *, ctx: Any, **kwargs: Any) -> tuple[list, str]:
        semantic_search = kwargs.get("search_semantic_only")
        if semantic_search is not None:
            docs = await semantic_search()
        else:
            search = kwargs["search_vector"]
            docs = await self._call_semantic_hint(search)
        if docs is False:
            docs = []
        return list(docs or []), "semantic_only"

    async def _call_semantic_hint(self, search: Any) -> Any:
        """Pass semantic_only hint when the port supports it."""
        try:
            sig = inspect.signature(search)
            if "semantic_only" in sig.parameters:
                return await search(semantic_only=True)
        except (TypeError, ValueError):
            pass
        return await search()
