"""Unit tests for StrategyRegistry and distinct strategy behaviors (022)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services.rag.skills.strategies import (
    DefaultRetrievalStrategy,
    DocumentLookupRetrievalStrategy,
    HybridRetrievalStrategy,
    PairLookupRetrievalStrategy,
    SemanticOnlyRetrievalStrategy,
    StrategyRegistry,
    get_retrieval_strategy,
    register_strategy,
)
from services.rag.skills.strategies.default import DefaultRetrievalStrategy as DefaultCls


class _Ctx:
    skill_id = "interactions"
    primary_entity = "Aspirin"


@pytest.mark.asyncio
async def test_default_strategy_uses_default_path() -> None:
    search = AsyncMock(return_value=[{"id": 1}])
    strategy = DefaultRetrievalStrategy()
    docs, path = await strategy.retrieve(
        ctx=None,
        search_vector=search,
        default_path="entity_scoped",
    )
    assert docs == [{"id": 1}]
    assert path == "entity_scoped"
    search.assert_awaited_once()


@pytest.mark.asyncio
async def test_semantic_only_distinct_path() -> None:
    search = AsyncMock(return_value=[{"id": 2}])
    strategy = SemanticOnlyRetrievalStrategy()
    docs, path = await strategy.retrieve(ctx=None, search_vector=search)
    assert path == "semantic_only"
    assert docs == [{"id": 2}]


@pytest.mark.asyncio
async def test_hybrid_prefers_hybrid_port() -> None:
    hybrid = AsyncMock(return_value=[{"id": 3}])
    search = AsyncMock(return_value=[])
    strategy = HybridRetrievalStrategy()
    docs, path = await strategy.retrieve(
        ctx=None,
        search_vector=search,
        hybrid_search=hybrid,
    )
    assert path == "hybrid"
    assert docs == [{"id": 3}]
    hybrid.assert_awaited_once()
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_hybrid_fallback_to_vector() -> None:
    search = AsyncMock(return_value=[{"id": 4}])
    strategy = HybridRetrievalStrategy()
    docs, path = await strategy.retrieve(ctx=None, search_vector=search)
    assert path == "hybrid_fallback→vector"
    assert docs == [{"id": 4}]


@pytest.mark.asyncio
async def test_document_lookup_path_label() -> None:
    search = AsyncMock(return_value=[{"id": 5}])
    strategy = DocumentLookupRetrievalStrategy()
    docs, path = await strategy.retrieve(ctx=None, search_vector=search)
    assert path == "document_lookup"
    assert docs == [{"id": 5}]


@pytest.mark.asyncio
async def test_pair_lookup_structured_hit() -> None:
    fetch = AsyncMock(return_value=([{"pair": True}], "tok"))
    search = AsyncMock()
    strategy = PairLookupRetrievalStrategy()
    docs, path = await strategy.retrieve(
        ctx=_Ctx(),
        search_vector=search,
        fetch_pair_documents=fetch,
    )
    assert path == "pair_lookup_structured"
    assert docs == [{"pair": True}]
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_pair_lookup_miss_falls_back() -> None:
    fetch = AsyncMock(return_value=([], None))
    search = AsyncMock(return_value=[{"vec": True}])
    strategy = PairLookupRetrievalStrategy()
    docs, path = await strategy.retrieve(
        ctx=_Ctx(),
        search_vector=search,
        fetch_pair_documents=fetch,
    )
    assert path == "pair_lookup_miss→vector"
    assert docs == [{"vec": True}]


@pytest.mark.asyncio
async def test_registry_get_unknown_falls_back_to_default() -> None:
    reg = StrategyRegistry()
    reg.register(DefaultCls())
    reg.register(PairLookupRetrievalStrategy())
    assert reg.get("nonexistent").name == "default"


@pytest.mark.asyncio
async def test_registry_execute_delegates() -> None:
    reg = StrategyRegistry()
    reg.register(DefaultRetrievalStrategy())
    search = AsyncMock(return_value=[])
    docs, path = await reg.execute("default", ctx=None, search_vector=search, default_path="vector")
    assert path == "vector"
    assert docs == []


def test_module_register_strategy_extends_registry() -> None:
    class _Custom:
        name = "custom_test_strategy"

        async def retrieve(self, *, ctx, **kwargs):
            return [], "custom"

    register_strategy(_Custom())
    assert get_retrieval_strategy("custom_test_strategy").name == "custom_test_strategy"
