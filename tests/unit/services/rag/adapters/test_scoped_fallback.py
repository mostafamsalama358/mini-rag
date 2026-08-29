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


@pytest.mark.asyncio
async def test_dense_field_soft_miss_keeps_subject_metadata_filter(monkeypatch):
    """Geography-style scope: extra.subject + field_key, no brand entity."""
    monkeypatch.setattr(
        "services.rag.adapters.vector_retriever.get_settings",
        lambda: SimpleNamespace(
            RAG_FIELD_SCORE_BOOST=0.15,
            RAG_FIELD_SCORE_PENALTY=0.08,
            RAG_ALLOW_UNSCOPED_DEGRADE=False,
        ),
    )
    monkeypatch.setattr(
        "services.rag.adapters.scope.get_settings",
        lambda: SimpleNamespace(RAG_ALLOW_UNSCOPED_DEGRADE=False),
    )
    vectordb = MagicMock()

    async def _scoped(**kwargs):
        if kwargs.get("field_key"):
            return []
        return [_doc("الصخور النارية والرسوبية والمتحولة")]

    vectordb.search_by_vector_scoped = AsyncMock(side_effect=_scoped)
    vectordb.search_by_vector = AsyncMock(return_value=[_doc("Bon voyage")])
    embedding = MagicMock()
    embedding.embed_text_async = AsyncMock(return_value=[0.1, 0.2])
    embedding.embedding_size = 768

    retriever = PgVectorDenseRetriever(
        vectordb_client=vectordb,
        embedding_client=embedding,
    )
    docs = await retriever.retrieve(
        RetrievalQuery(
            query_text="أقسام صخور القشرة",
            strategy="dense",
            expander_variant_id="base",
        ),
        RetrievalContext(
            plan_id="p1",
            policy=ExecutionPolicy(),
            metadata={
                "collection_name": "collection_768_5",
                "field_key": "explanation",
                "metadata_filter": {"subject": "geography"},
                "limit": 8,
            },
        ),
    )

    assert len(docs) == 1
    assert "النارية" in docs[0].content_excerpt
    assert vectordb.search_by_vector_scoped.await_count == 2
    retry = vectordb.search_by_vector_scoped.await_args_list[1]
    assert retry.kwargs.get("field_key") is None
    assert retry.kwargs.get("metadata_filter") == {"subject": "geography"}
    vectordb.search_by_vector.assert_not_awaited()
