"""Unit tests for RetrievedDocument ↔ RawCandidate round-trips."""

from __future__ import annotations

import pytest

from models.db_schemes import RetrievedDocument
from services.rag.adapters.type_mapping import (
    raw_candidate_to_retrieved_document,
    raw_candidates_to_evidence_items,
    retrieved_document_to_raw_candidate,
)


def test_retrieved_document_round_trip_preserves_text_score_ids():
    doc = RetrievedDocument(
        text="ibuprofen dose",
        score=0.91,
        metadata={"chunk_id": "c1", "document_id": "d1", "page_number": 2},
    )
    candidate = retrieved_document_to_raw_candidate(doc, retriever_id="pgvector_dense")
    restored = raw_candidate_to_retrieved_document(candidate)
    assert restored.text == "ibuprofen dose"
    assert restored.score == pytest.approx(0.91)
    assert restored.metadata["chunk_id"] == "c1"
    assert restored.metadata["document_id"] == "d1"
    assert candidate.retriever_id == "pgvector_dense"


def test_raw_candidates_to_evidence_items():
    doc = RetrievedDocument(
        text="hello",
        score=0.5,
        metadata={"chunk_id": "c9", "document_id": "d9"},
    )
    candidate = retrieved_document_to_raw_candidate(doc)
    items = raw_candidates_to_evidence_items([candidate])
    assert len(items) == 1
    assert items[0].candidate.chunk_id == "c9"
    assert items[0].strategy_id == "semantic"
