"""Unit tests for SparseRetriever."""

from __future__ import annotations

import pytest

from core.retrieval_engine.models import RetrievalContext, RetrievalQuery
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_engine.retrievers.sparse import SparseRetriever
from core.retrieval_planner.models import QueryFilter, compute_filter_id


class _Fts:
    def __init__(self) -> None:
        self.seen_filters = None

    def search(self, query_text, filters=None):
        self.seen_filters = filters
        return [
            {
                "chunk_id": "k1",
                "document_id": "d1",
                "score": 0.8,
                "content_excerpt": query_text,
            }
        ]


@pytest.mark.asyncio
async def test_sparse_retriever():
    store = _Fts()
    ret = SparseRetriever(store)
    assert ret.retriever_id == "sparse_fts"
    assert ret.supported_strategy == "keyword"
    flt = QueryFilter(
        filter_id=compute_filter_id("category", "field", "eq", "x"),
        filter_type="category",
        field_name="field",
        operator="eq",
        value="x",
        source="explicit",
    )
    ctx = RetrievalContext(
        plan_id="rp_x",
        filters=(flt,),
        constraints=None,
        hints=None,
        policy=ExecutionPolicy(),
    )
    out = await ret.retrieve(
        RetrievalQuery(query_text="q", strategy="keyword", expander_variant_id="v0"),
        ctx,
    )
    assert store.seen_filters == (flt,)
    assert len(out) == 1
    assert out[0].chunk_id == "k1"
