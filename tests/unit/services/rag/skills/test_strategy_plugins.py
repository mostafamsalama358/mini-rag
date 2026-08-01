"""US3 — mandatory strategies produce distinct path labels."""

from __future__ import annotations

import pytest

from services.rag.skills.strategies import StrategyRegistry, get_retrieval_strategy
from services.rag.skills.strategies.default import DefaultRetrievalStrategy
from services.rag.skills.strategies.document_lookup import DocumentLookupRetrievalStrategy
from services.rag.skills.strategies.hybrid import HybridRetrievalStrategy
from services.rag.skills.strategies.pair_lookup import PairLookupRetrievalStrategy
from services.rag.skills.strategies.semantic_only import SemanticOnlyRetrievalStrategy


class _Ctx:
    primary_entity = "Panadol"
    skill_id = "interactions"
    retrieval_strategy = "pair_lookup"


@pytest.mark.asyncio
async def test_strategies_distinct_path_labels() -> None:
    async def search_vector(**kwargs):
        return [{"id": "v"}]

    async def fetch_pair(*, entity: str):
        return [{"id": "pair"}], "tok"

    async def hybrid_search(**kwargs):
        return [{"id": "h"}]

    paths: dict[str, str] = {}

    for name, strat in (
        ("default", DefaultRetrievalStrategy()),
        ("semantic_only", SemanticOnlyRetrievalStrategy()),
        ("hybrid", HybridRetrievalStrategy()),
        ("document_lookup", DocumentLookupRetrievalStrategy()),
        ("pair_lookup", PairLookupRetrievalStrategy()),
    ):
        docs, path = await strat.retrieve(
            ctx=_Ctx(),
            search_vector=search_vector,
            fetch_pair_documents=fetch_pair,
            hybrid_search=hybrid_search,
            default_path="vector",
        )
        paths[name] = path
        assert docs

    assert paths["semantic_only"] == "semantic_only"
    assert paths["document_lookup"] == "document_lookup"
    assert paths["pair_lookup"] == "pair_lookup_structured"
    assert paths["hybrid"] in ("hybrid", "hybrid_fallback→vector")
    assert paths["default"] in ("vector", "default", "entity_scoped")
    assert len(set(paths.values())) >= 4


def test_get_retrieval_strategy_resolves_all_mandatory() -> None:
    for name in ("default", "semantic_only", "hybrid", "document_lookup", "pair_lookup"):
        assert get_retrieval_strategy(name).name == name
