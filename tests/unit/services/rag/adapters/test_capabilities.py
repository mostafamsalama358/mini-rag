"""Unit tests for AdapterCapabilities."""

from __future__ import annotations

import dataclasses

import pytest

from services.rag.adapters.capabilities import AdapterCapabilities
from services.rag.adapters.sparse_retriever import PgVectorSparseRetriever
from services.rag.adapters.vector_retriever import PgVectorDenseRetriever
from services.rag.adapters.interaction_retriever import StructuredInteractionRetriever


def test_adapter_capabilities_is_frozen():
    caps = AdapterCapabilities(
        retriever_id="pgvector_dense",
        supported_strategy="dense",
        features=frozenset({"dense_vector"}),
    )
    assert caps.retriever_id == "pgvector_dense"
    assert caps.supported_strategy == "dense"
    assert "dense_vector" in caps.features
    with pytest.raises(dataclasses.FrozenInstanceError):
        caps.retriever_id = "other"  # type: ignore[misc]


def test_dense_retriever_exposes_capabilities():
    assert PgVectorDenseRetriever.CAPABILITIES.retriever_id == "pgvector_dense"
    assert PgVectorDenseRetriever.CAPABILITIES.supported_strategy == "dense"
    assert "scoped_search" in PgVectorDenseRetriever.CAPABILITIES.features


def test_sparse_and_interaction_capabilities():
    assert PgVectorSparseRetriever.CAPABILITIES.supported_strategy == "sparse"
    assert (
        StructuredInteractionRetriever.CAPABILITIES.supported_strategy
        == "structured_interaction"
    )
