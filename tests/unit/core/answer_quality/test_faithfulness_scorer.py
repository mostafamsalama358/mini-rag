"""Unit tests for TextFaithfulnessScorer."""

from __future__ import annotations

import pytest

from core.answer_quality.faithfulness.scorer import TextFaithfulnessScorer
from tests.unit.core.answer_quality.conftest import (
    build_answer_result,
    build_context,
    build_golden_fixture,
    default_config,
)


@pytest.mark.asyncio
async def test_all_claims_in_corpus(default_config) -> None:
    context = build_context(
        block_texts=["The standard dose is 325 mg every 4 hours."]
    )
    answer = build_answer_result(answer="Take 325 mg every 4 hours.")
    fixture = build_golden_fixture("q001")

    result = await TextFaithfulnessScorer().score(
        fixture, answer, context, default_config
    )

    assert result.faithfulness_score == pytest.approx(1.0)
    assert result.passed is True
    assert result.unsupported_claims == []


@pytest.mark.asyncio
async def test_fabricated_number_detected(default_config) -> None:
    context = build_context(
        block_texts=["The standard dose is 325 mg every 4 hours."]
    )
    answer = build_answer_result(answer="Take 500 mg every 4 hours.")
    fixture = build_golden_fixture("q001")

    result = await TextFaithfulnessScorer().score(
        fixture, answer, context, default_config
    )

    assert result.faithfulness_score is not None
    assert result.faithfulness_score < 1.0
    assert any("500" in claim for claim in result.unsupported_claims)
    assert result.passed is False


@pytest.mark.asyncio
async def test_no_answer_is_not_applicable(default_config) -> None:
    context = build_context(block_texts=["Some source text."])
    answer = build_answer_result(answer="No answer.", no_answer=True)
    fixture = build_golden_fixture("q001")

    result = await TextFaithfulnessScorer().score(
        fixture, answer, context, default_config
    )

    assert result.not_applicable is True
    assert result.passed is True


@pytest.mark.asyncio
async def test_empty_ordered_blocks_is_not_applicable(default_config) -> None:
    context = build_context(block_texts=[])
    answer = build_answer_result(answer="Some answer.")
    fixture = build_golden_fixture("q001")

    result = await TextFaithfulnessScorer().score(
        fixture, answer, context, default_config
    )

    assert result.not_applicable is True
    assert result.passed is True


@pytest.mark.asyncio
async def test_whitespace_only_answer_is_not_applicable(default_config) -> None:
    context = build_context(block_texts=["Some source text."])
    answer = build_answer_result(answer=" ")
    fixture = build_golden_fixture("q001")

    result = await TextFaithfulnessScorer().score(
        fixture, answer, context, default_config
    )

    assert result.not_applicable is True
    assert result.passed is True
