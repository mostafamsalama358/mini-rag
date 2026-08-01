"""Structured interaction retriever adapter (spec 015)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.retrieval_engine.interfaces import IRetriever
from core.retrieval_engine.models import RawCandidate, RetrievalContext, RetrievalQuery
from repositories.chunk_repository import ChunkModel
from services.rag.adapters.capabilities import AdapterCapabilities
from services.rag.adapters.type_mapping import retrieved_document_to_raw_candidate
from services.rag.interaction_retrieval import fetch_interaction_documents

logger = logging.getLogger("uvicorn.error")


class StructuredInteractionRetriever(IRetriever):
    """Domain structured interaction lookup via fetch_interaction_documents."""

    CAPABILITIES = AdapterCapabilities(
        retriever_id="structured_interaction",
        supported_strategy="structured_interaction",
        features=frozenset({"structured_interaction"}),
    )

    def __init__(
        self,
        *,
        db_client: Any = None,
        chunk_model: Any = None,
    ) -> None:
        self._db_client = db_client
        self._chunk_model = chunk_model

    @property
    def retriever_id(self) -> str:
        return self.CAPABILITIES.retriever_id

    @property
    def supported_strategy(self) -> str:
        return self.CAPABILITIES.supported_strategy

    async def _get_chunk_model(self):
        if self._chunk_model is not None:
            return self._chunk_model
        if self._db_client is None:
            return None
        return await ChunkModel.create_instance(self._db_client)

    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]:
        meta = context.metadata or {}
        project_id = meta.get("project_id")
        entity = meta.get("entity") or meta.get("entity_prefix")
        field_manifest = meta.get("field_manifest")
        registry = meta.get("field_registry")
        limit = int(meta.get("limit") or meta.get("max_candidates") or 500)

        if project_id is None or not entity or field_manifest is None or registry is None:
            return []

        try:
            chunk_model = await self._get_chunk_model()
            if chunk_model is None:
                return []
            docs, _token = await fetch_interaction_documents(
                project_id=int(project_id),
                entity=str(entity),
                chunk_model=chunk_model,
                field_manifest=field_manifest,
                registry=registry,
                limit=limit,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — miss → empty; engine fallbacks
            logger.warning(
                "structured_interaction_miss plan_id=%s err=%s",
                context.plan_id,
                exc,
            )
            return []

        if not docs:
            return []

        return [
            retrieved_document_to_raw_candidate(
                doc,
                retriever_id=self.retriever_id,
                strategy=query.strategy or self.supported_strategy,
                expander_variant_id=query.expander_variant_id,
            )
            for doc in docs
        ]
