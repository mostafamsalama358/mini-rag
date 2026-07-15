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
        expected_answer_facets=["325 mg", "every 4 hours"],
    )
    answer = build_answer_result(
        answer="The dose is 325 mg taken every 4 hours."
    )

    result = await KeywordCompletenessScorer().score(fixture, answer, default_config)

    assert result.completeness_score == pytest.approx(1.0)
    assert result.passed is True
    assert result.uncovered_facets == []


@pytest.mark.asyncio
async def test_partial_facets_covered(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        expected_answer_facets=["325 mg", "avoid if allergic to aspirin"],
    )
    answer = build_answer_result(answer="The dose is 325 mg per tablet.")

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
