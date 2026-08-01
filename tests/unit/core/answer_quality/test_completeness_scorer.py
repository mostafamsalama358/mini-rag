"""Unit tests for KeywordCompletenessScorer."""

from __future__ import annotations

import pytest

from core.answer_quality.completeness.scorer import KeywordCompletenessScorer
from tests.unit.core.answer_quality.conftest import (
    build_answer_result,
    build_golden_fixture,
    default_config,
)


@pytest.mark.asyncio
async def test_all_facets_covered(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        question="What is the adult dose of aspirin?",
        expected_answer_facets=["325 mg", "every 4 hours"],
    )
    answer = build_answer_result(
        answer="The adult dose of aspirin is 325 mg taken every 4 hours."
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(1.0)
    assert result.passed is True
    assert result.uncovered_facets == []


@pytest.mark.asyncio
async def test_partial_facets_covered(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        question="What is the dose and allergy warning for aspirin?",
        expected_answer_facets=["325 mg", "avoid if allergic to aspirin"],
    )
    answer = build_answer_result(
        answer="The aspirin dose is 325 mg per tablet."
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(0.5)
    assert "325 mg" in result.covered_facets
    assert "avoid if allergic to aspirin" in result.uncovered_facets
    assert result.passed is False


@pytest.mark.asyncio
async def test_no_expected_facets_is_not_applicable(default_config) -> None:
    fixture = build_golden_fixture("q001", expected_answer_facets=None)
    answer = build_answer_result(answer="Any answer.")

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.not_applicable is True
    assert result.passed is True


@pytest.mark.asyncio
async def test_no_answer_is_not_applicable(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        expected_answer_facets=["325 mg"],
    )
    answer = build_answer_result(answer="No answer.", no_answer=True)

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.not_applicable is True
    assert result.passed is True


@pytest.mark.asyncio
async def test_topic_summary_keyword_stuffing_fails(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        question="What are the contraindications for aspirin?",
        expected_answer_facets=[
            "allergic reactions",
            "bleeding disorder",
            "dosage warnings",
        ],
    )
    answer = build_answer_result(
        answer=(
            "This document discusses aspirin allergic reactions, bleeding disorder "
            "risk, aspirin dosage warnings, and general aspirin safety information "
            "for patients."
        )
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(0.0)
    assert result.passed is False


@pytest.mark.asyncio
async def test_comma_list_stuffing_without_document_phrase_fails(default_config) -> None:
    """F3 variant: noun dump of facet keywords, no 'this document discusses'."""
    fixture = build_golden_fixture(
        "q001",
        question="What are the contraindications for aspirin?",
        expected_answer_facets=["allergic to aspirin", "bleeding disorder"],
    )
    answer = build_answer_result(
        answer=(
            "Aspirin allergic reactions, bleeding disorder risk, aspirin dosage "
            "warnings, and aspirin safety."
        )
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(0.0)
    assert result.passed is False


@pytest.mark.asyncio
async def test_overview_meta_phrasing_fails(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        question="What are the side effects of aspirin?",
        expected_answer_facets=["stomach upset", "heartburn", "nausea"],
    )
    answer = build_answer_result(
        answer=(
            "This section provides an overview of stomach upset, heartburn, nausea, "
            "and related topics."
        )
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(0.0)
    assert result.passed is False


@pytest.mark.asyncio
async def test_real_contraindication_answer_passes(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        question="What are the contraindications for aspirin?",
        expected_answer_facets=["allergic to aspirin", "bleeding disorder"],
    )
    answer = build_answer_result(
        answer=(
            "Avoid aspirin if you are allergic to aspirin. "
            "It is also contraindicated in patients with an active bleeding disorder."
        )
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(1.0)
    assert result.passed is True


@pytest.mark.asyncio
async def test_facet_in_meta_sentence_does_not_count(default_config) -> None:
    """Facet tokens inside a meta sentence must not count as coverage."""
    fixture = build_golden_fixture(
        "q001",
        question="What are the contraindications for aspirin?",
        expected_answer_facets=["bleeding disorder"],
    )
    answer = build_answer_result(
        answer="This article mentions bleeding disorder among other topics."
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(0.0)
    assert result.passed is False


@pytest.mark.asyncio
async def test_side_effects_include_list_passes(default_config) -> None:
    """Legitimate 'effects include A, B, and C' must not be treated as stuffing."""
    fixture = build_golden_fixture(
        "q001",
        question="What are the side effects of aspirin?",
        expected_answer_facets=["stomach upset", "heartburn", "nausea"],
    )
    answer = build_answer_result(
        answer="Common side effects include stomach upset, heartburn, and nausea."
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(1.0)
    assert result.passed is True


@pytest.mark.asyncio
async def test_navigational_section_covers_passes(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        question="Where is the interactions section for aspirin?",
        expected_answer_facets=["warfarin", "peptic ulcer"],
    )
    answer = build_answer_result(
        answer=(
            "The interactions section covers warfarin and peptic ulcer precautions."
        )
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(1.0)
    assert result.passed is True
