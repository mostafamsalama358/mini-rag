"""Unit tests for StructuredRetriever."""

from __future__ import annotations

import pytest

from core.retrieval_engine.models import RetrievalContext, RetrievalQuery
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_engine.retrievers.structured import StructuredRetriever
from core.retrieval_planner.models import ExecutionHints


class _Struct:
    def __init__(self) -> None:
        self.kwargs = None

    def search(self, query_text, **kwargs):
        self.kwargs = kwargs
        return [
            {
                "chunk_id": "s1",
                "document_id": "d1",
                "score": 0.95,
                "content_excerpt": "row: a=1",
            }
        ]


@pytest.mark.asyncio
async def test_structured_retriever():
    store = _Struct()
    ret = StructuredRetriever(store)
    assert ret.supported_strategy == "structured"
    assert ret.experimental is False
    hints = ExecutionHints(allow_table_search=True, preferred_section_kinds=["table"])
    ctx = RetrievalContext(
        plan_id="rp_x",
        filters=(),
        constraints=None,
        hints=hints,
        policy=ExecutionPolicy(),
    )
    out = await ret.retrieve(
        RetrievalQuery(query_text="q", strategy="structured", expander_variant_id="v0"),
        ctx,
    )
    assert store.kwargs["allow_table_search"] is True
    assert store.kwargs["preferred_section_kinds"] == ["table"]
    assert out[0].chunk_id == "s1"
