"""Integration tests for Answer Generation (spec 013)."""

from __future__ import annotations

import json

import pytest

from core.answer_generation.config import resolve_answer_generation_config
from core.answer_generation.registry import AnswerGenerationRegistry
from core.context_builder.models import ConflictGroup
from tests.unit.core.answer_generation.conftest import (
    MockLLM,
    make_context,
    make_two_block_context,
)


@pytest.mark.asyncio
async def test_cited_answer_happy_path() -> None:
    llm = MockLLM()
    config = resolve_answer_generation_config("generic")
    pipeline = AnswerGenerationRegistry.build(config, llm)
    context = make_two_block_context()

    result = await pipeline.run(
        context=context,
        question="What is the adult dose?",
        config=config,
    )

    assert result.no_answer is False
    assert len(result.citations) == 1
    assert result.citations[0].citation_id in context.citation_map
    assert result.schema_version == "1.0.0"


@pytest.mark.asyncio
async def test_citation_count_matches_marker_count() -> None:
    llm = MockLLM(
        response=json.dumps(
            {
                "answer": (
                    "Dose A [ei_aaaa000000000001] and caution "
                    "[ei_bbbb000000000002]."
                ),
                "confidence_note": None,
            }
        )
    )
    config = resolve_answer_generation_config("generic")
    pipeline = AnswerGenerationRegistry.build(config, llm)

    result = await pipeline.run(
        context=make_two_block_context(),
        question="Summarize?",
        config=config,
    )

    assert len(result.citations) == 2


@pytest.mark.asyncio
async def test_conflict_disclosure() -> None:
    conflict = ConflictGroup(
        entity_tag="paracetamol",
        attribute="max_daily_dose",
        item_ids=["ei_aaaa000000000001", "ei_bbbb000000000002"],
    )
    context = make_two_block_context().model_copy(update={"conflicts": [conflict]})
    llm = MockLLM(
        response=json.dumps(
            {
                "answer": (
                    "Conflicting information exists. Dose is 500 mg "
                    "[ei_aaaa000000000001]."
                ),
                "confidence_note": None,
            }
        )
    )
    config = resolve_answer_generation_config("generic")
    pipeline = AnswerGenerationRegistry.build(config, llm)

    result = await pipeline.run(
        context=context,
        question="What is the dose?",
        config=config,
    )

    assert result.conflicts_disclosed is True
    assert "conflict" in result.answer.lower() or "conflicting" in result.answer.lower()


@pytest.mark.asyncio
async def test_no_answer_empty_context() -> None:
    llm = MockLLM()
    config = resolve_answer_generation_config("generic")
    pipeline = AnswerGenerationRegistry.build(config, llm)
    empty_context = make_context(blocks=[], citation_map={})

    result = await pipeline.run(
        context=empty_context,
        question="Anything?",
        config=config,
    )

    assert result.no_answer is True
    assert result.answer == config.no_answer_message
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_provider_swap_identical_result_shape() -> None:
    context = make_two_block_context()
    config = resolve_answer_generation_config("generic")
    response = json.dumps(
        {
            "answer": "500 mg [ei_aaaa000000000001].",
            "confidence_note": "ok",
        }
    )

    llm_a = MockLLM(response=response)
    llm_b = MockLLM(response=response)

    result_a = await AnswerGenerationRegistry.build(config, llm_a).run(
        context=context,
        question="Dose?",
        config=config,
    )
    result_b = await AnswerGenerationRegistry.build(config, llm_b).run(
        context=context,
        question="Dose?",
        config=config,
    )

    assert result_a.model_dump().keys() == result_b.model_dump().keys()
    assert result_a.citations[0].citation_id == result_b.citations[0].citation_id


@pytest.mark.asyncio
async def test_grounding_flag() -> None:
    from tests.unit.core.answer_generation.conftest import make_block

    context = make_context(
        blocks=[
            make_block(
                item_id="ei_aaaa000000000001",
                text="Metformin is used for type 2 diabetes.",
            )
        ]
    )
    llm = MockLLM(
        response=json.dumps(
            {
                "answer": "The patient should take Metformin XR daily.",
                "confidence_note": None,
            }
        )
    )
    config = resolve_answer_generation_config("generic")
    pipeline = AnswerGenerationRegistry.build(config, llm)

    result = await pipeline.run(
        context=context,
        question="What should they take?",
        config=config,
    )

    assert result.answer
    assert any(flag.entity == "Metformin XR" for flag in result.grounding_flags)
