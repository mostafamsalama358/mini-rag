"""Skill extra.subject must not be dropped when a logical field_key is set."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.rag.rag_service import NLPController


class _FakeVectorDB:
    def __init__(self) -> None:
        self.scoped_calls: list[dict] = []
        self.field_calls: list[dict] = []
        self.search_by_vector_scoped = AsyncMock(side_effect=self._scoped)
        self.search_by_vector_field = AsyncMock(side_effect=self._field)

    async def _scoped(self, **kwargs):
        self.scoped_calls.append(kwargs)
        return [SimpleNamespace(text="geo toc", score=0.8, metadata={"subject": "geography"})]

    async def _field(self, **kwargs):
        self.field_calls.append(kwargs)
        return [SimpleNamespace(text="Bon voyage", score=0.9, metadata={"subject": "french"})]


@pytest.mark.asyncio
async def test_fetch_uses_scoped_search_when_subject_and_field_are_set():
    vectordb = _FakeVectorDB()
    ctrl = object.__new__(NLPController)
    ctrl.vectordb_client = vectordb

    dense, sparse = await ctrl._fetch_dense_and_sparse_candidates(
        collection_name="collection_768_5",
        query_vector=[0.1, 0.2],
        text="أقسام صخور القشرة",
        metadata_filter={"subject": "geography"},
        candidates=8,
        hybrid_enabled=False,
        field_resolution=SimpleNamespace(column_keys=("explanation",)),
    )

    assert dense and dense[0].text == "geo toc"
    assert sparse == []
    assert vectordb.field_calls == []
    assert len(vectordb.scoped_calls) == 1
    call = vectordb.scoped_calls[0]
    assert call["metadata_filter"] == {"subject": "geography"}
    assert call["field_key"] == "explanation"
    vectordb.search_by_vector_field.assert_not_awaited()
