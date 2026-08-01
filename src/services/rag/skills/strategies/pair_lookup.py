"""Structured pair/interaction lookup with vector fallback."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("uvicorn.error")


class PairLookupRetrievalStrategy:
    name = "pair_lookup"

    async def retrieve(self, *, ctx: Any, **kwargs: Any) -> tuple[list, str]:
        fetch_pair = kwargs.get("fetch_pair_documents")
        search = kwargs["search_vector"]
        entity = getattr(ctx, "primary_entity", None) if ctx is not None else None
        skill_id = getattr(ctx, "skill_id", None) if ctx is not None else None
        if fetch_pair is not None and entity:
            docs, _token = await fetch_pair(entity=entity)
            if docs:
                return list(docs), "pair_lookup_structured"
            logger.info(
                "pair_lookup_miss skill_id=%s entity=%r — falling back to vector",
                skill_id,
                entity,
            )
            docs = await search()
            if docs is False:
                docs = []
            return list(docs or []), "pair_lookup_miss→vector"
        docs = await search()
        if docs is False:
            docs = []
        return list(docs or []), "pair_lookup_vector"
