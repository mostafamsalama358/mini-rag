"""Scoped retrieve falls back to unscoped when metadata filters miss."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.retrieval_engine.models import RetrievalContext, RetrievalQuery
from core.retrieval_engine.policies import ExecutionPolicy
from services.rag.adapters.sparse_retriever import PgVectorSparseRetriever
from services.rag.adapters.vector_retriever import PgVectorDenseRetriever


def _doc(text: str = "ibuprofen 200mg") -> SimpleNamespace:
    return SimpleNamespace(text=text, score=0.9, metadata={})


@pytest.mark.asyncio
async def test_dense_scoped_miss_falls_back_unscoped():
    vectordb = MagicMock()
    vectordb.search_by_vector_scoped = AsyncMock(return_value=[])
    vectordb.search_by_vector = AsyncMock(return_value=[_doc()])
    embedding = MagicMock()
    embedding.embed_text_async = AsyncMock(return_value=[0.1, 0.2])
    embedding.embedding_size = 1024

    retriever = PgVectorDenseRetriever(
        vectordb_client=vectordb,
        embedding_client=embedding,
    )
    docs = await retriever.retrieve(
        RetrievalQuery(
            query_text="ibuprofen dose",
            strategy="dense",
            expander_variant_id="base",
        ),
        RetrievalContext(
            plan_id="p1",
            policy=ExecutionPolicy(),
            metadata={
                "collection_name": "collection_1024_2",
                "entity_key": "trade_name",
                "entity_prefix": "IBUPROFEN",
                "field_key": "dosage",
                "limit": 5,
            },
        ),
    )

    assert len(docs) == 1
    vectordb.search_by_vector_scoped.assert_awaited_once()
    vectordb.search_by_vector.assert_awaited_once()


@pytest.mark.asyncio
async def test_dense_scoped_collection_missing_no_fallback():
    vectordb = MagicMock()
    vectordb.search_by_vector_scoped = AsyncMock(return_value=False)
    vectordb.search_by_vector = AsyncMock(return_value=[_doc()])
    embedding = MagicMock()
    embedding.embed_text_async = AsyncMock(return_value=[0.1, 0.2])

    retriever = PgVectorDenseRetriever(
        vectordb_client=vectordb,
        embedding_client=embedding,
    )
    docs = await retriever.retrieve(
        RetrievalQuery(
            query_text="ibuprofen dose",
            strategy="dense",
            expander_variant_id="base",
        ),
        RetrievalContext(
            plan_id="p1",
            policy=ExecutionPolicy(),
            metadata={
                "collection_name": "collection_1024_2",
                "entity_key": "trade_name",
                "entity_prefix": "IBUPROFEN",
                "limit": 5,
            },
        ),
    )

    assert docs == []
    vectordb.search_by_vector.assert_not_awaited()


@pytest.mark.asyncio
async def test_sparse_scoped_miss_falls_back_unscoped():
    vectordb = MagicMock()
    vectordb.search_by_text_scoped = AsyncMock(return_value=[])
    vectordb.search_by_text = AsyncMock(return_value=[_doc()])

    retriever = PgVectorSparseRetriever(vectordb_client=vectordb)
    docs = await retriever.retrieve(
        RetrievalQuery(
            query_text="ibuprofen dose",
            strategy="sparse",
            expander_variant_id="base",
        ),
        RetrievalContext(
            plan_id="p1",
            policy=ExecutionPolicy(),
            metadata={
                "collection_name": "collection_1024_2",
                "entity_key": "trade_name",
                "entity_prefix": "IBUPROFEN",
                "field_key": "dosage",
                "limit": 5,
            },
        ),
    )

    assert len(docs) == 1
    vectordb.search_by_text_scoped.assert_awaited_once()
    vectordb.search_by_text.assert_awaited_once()
