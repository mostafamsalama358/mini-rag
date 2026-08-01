"""Default vector retrieval strategy."""

from __future__ import annotations

from typing import Any


class DefaultRetrievalStrategy:
    name = "default"

    async def retrieve(self, *, ctx: Any, **kwargs: Any) -> tuple[list, str]:
        search = kwargs["search_vector"]
        docs = await search()
        if docs is False:
            docs = []
        path = kwargs.get("default_path") or "vector"
        return list(docs or []), path
