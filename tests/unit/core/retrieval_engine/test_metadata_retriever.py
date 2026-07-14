"""Unit tests for MetadataRetriever."""

from __future__ import annotations

import pytest

from core.retrieval_engine.models import RetrievalContext, RetrievalQuery
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_engine.retrievers.metadata import MetadataRetriever
from core.retrieval_planner.models import QueryFilter, compute_filter_id


class _Meta:
    def __init__(self) -> None:
        self.seen_filters = None

    def search(self, query_text, filters=None):
        self.seen_filters = filters
        return [
            {
                "chunk_id": "m1",
                "document_id": "d1",
                "score": 0.7,
                "text": "meta hit",
            }
        ]


@pytest.mark.asyncio
async def test_metadata_retriever():
    store = _Meta()
    ret = MetadataRetriever(store)
    assert ret.retriever_id == "metadata_filter"
    assert ret.supported_strategy == "metadata"
    flt = QueryFilter(
        filter_id=compute_filter_id("category", "doc_type", "eq", "policy"),
        filter_type="category",
        field_name="doc_type",
        operator="eq",
        value="policy",
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
        RetrievalQuery(query_text="q", strategy="metadata", expander_variant_id="v0"),
        ctx,
    )
    assert store.seen_filters == (flt,)
    assert out[0].chunk_id == "m1"
    assert out[0].content_excerpt == "meta hit"
