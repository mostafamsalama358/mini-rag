"""Unit tests for Answer Generation domain models."""

from __future__ import annotations

import pytest

from core.answer_generation.models import (
    AnswerResult,
    CitationReference,
    GroundingFlag,
    SCHEMA_VERSION,
)


def test_answer_result_happy_path() -> None:
    result = AnswerResult(
        answer="Dose is 500 mg.",
        citations=[
            CitationReference(
                citation_id="ei_aaaa000000000001",
                document_id="doc_001",
                chunk_id="chunk_01",
                retrieval_score=0.9,
            )
        ],
        plan_id="plan_test001",
        context_id="ctx_test0000000001",
    )
    assert result.schema_version == SCHEMA_VERSION
    assert result.no_answer is False


def test_answer_result_no_answer_requires_empty_citations() -> None:
    with pytest.raises(ValueError, match="citations must be empty"):
        AnswerResult(
            answer="No answer found.",
            citations=[
                CitationReference(
                    citation_id="ei_aaaa000000000001",
                    document_id="doc_001",
                    chunk_id="chunk_01",
                    retrieval_score=0.9,
                )
            ],
            no_answer=True,
            plan_id="plan_test001",
            context_id="ctx_test0000000001",
        )


def test_citation_reference_and_grounding_flag() -> None:
    citation = CitationReference(
        citation_id="ei_aaaa000000000001",
        document_id="doc_001",
        chunk_id="chunk_01",
        retrieval_score=0.5,
        document_title="BNF",
    )
    flag = GroundingFlag(
        entity="Metformin XR",
        claim="Patient should take Metformin XR daily.",
        reason="entity_not_in_context",
    )
    assert citation.document_title == "BNF"
    assert flag.reason == "entity_not_in_context"
