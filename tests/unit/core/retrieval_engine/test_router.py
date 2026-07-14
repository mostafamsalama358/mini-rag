"""Unit tests for StrategyRouter."""

from __future__ import annotations

import pytest

from core.retrieval_engine.errors import RetrieverNotFoundError
from core.retrieval_engine.router import StrategyRouter
from tests.unit.core.retrieval_engine.conftest import mock_retriever


def test_registered_retriever_routes():
    ret = mock_retriever("semantic")
    router = StrategyRouter(lambda s: ret if s == "semantic" else None)
    assert router.route("semantic") is ret


def test_unregistered_raises():
    router = StrategyRouter(lambda s: None)
    with pytest.raises(RetrieverNotFoundError):
        router.route("missing")


def test_hybrid_assertion():
    router = StrategyRouter(lambda s: None)
    with pytest.raises(AssertionError):
        router.route("hybrid")
