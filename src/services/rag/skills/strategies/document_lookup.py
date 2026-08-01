"""Entity-scoped document lookup — field-targeted leaflet retrieval."""

from __future__ import annotations

from typing import Any


class DocumentLookupRetrievalStrategy:
    name = "document_lookup"

    async def retrieve(self, *, ctx: Any, **kwargs: Any) -> tuple[list, str]:
        entity_search = kwargs.get("entity_scoped_search")
        if entity_search is not None:
            docs = await entity_search()
        else:
            search = kwargs["search_vector"]
            docs = await search()
        if docs is False:
            docs = []
        return list(docs or []), "document_lookup"
