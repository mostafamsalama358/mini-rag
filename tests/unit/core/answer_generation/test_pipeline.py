"""Unit tests for AnswerGenerationPipeline."""

from __future__ import annotations

import json
import logging

import pytest

from core.answer_generation.citation.item_id_formatter import ItemIdCitationFormatter
from core.answer_generation.composition.default_composer import DefaultPromptComposer
from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.errors import SchemaVersionError
from core.answer_generation.grounding.entity_tag_checker import EntityTagGroundingChecker
from core.answer_generation.interfaces import IGroundingChecker
from core.answer_generation.parsing.json_output_parser import JsonOutputParser
from core.answer_generation.pipeline import AnswerGenerationPipeline
from core.context_builder.models import ConflictGroup
from tests.unit.core.answer_generation.conftest import (
    MockLLM,
    make_block,
    make_context,
    make_two_block_context,
)


class NoOpGroundingChecker(IGroundingChecker):
    def check(self, answer_text, context):
        _ = answer_text, context
        return []


def _pipeline(
    llm: MockLLM,
    *,
    grounding_checker: IGroundingChecker | None = None,
) -> AnswerGenerationPipeline:
    return AnswerGenerationPipeline(
        composer=DefaultPromptComposer(),
        parser=JsonOutputParser(),
        citation_formatter=ItemIdCitationFormatter(),
        grounding_checker=grounding_checker or EntityTagGroundingChecker(),
        llm=llm,
    )


@pytest.mark.asyncio
async def test_happy_path_returns_cited_answer(
    default_config: AnswerGenerationConfig,
    sample_context,
    mock_llm: MockLLM,
) -> None:
    pipeline = _pipeline(mock_llm)
    result = await pipeline.run(
        context=sample_context,
        question="What is the adult dose?",
        config=default_config,
    )

    assert result.no_answer is False
    assert len(result.citations) == 1
    assert result.citations[0].citation_id == "ei_aaaa000000000001"
    assert mock_llm.call_count == 1


@pytest.mark.asyncio
async def test_schema_version_mismatch_raises(
    default_config: AnswerGenerationConfig,
    sample_context,
    mock_llm: MockLLM,
) -> None:
    bad_context = sample_context.model_copy(update={"schema_version": "2.0.0"})
    pipeline = _pipeline(mock_llm)

    with pytest.raises(SchemaVersionError):
        await pipeline.run(
            context=bad_context,
            question="Question?",
            config=default_config,
        )

    assert mock_llm.call_count == 0


@pytest.mark.asyncio
async def test_no_answer_empty_context(
    default_config: AnswerGenerationConfig,
    mock_llm: MockLLM,
) -> None:
    empty_context = make_context(blocks=[], citation_map={})
    pipeline = _pipeline(mock_llm)

    result = await pipeline.run(
        context=empty_context,
        question="Anything?",
        config=default_config,
    )

    assert result.no_answer is True
    assert result.citations == []
    assert result.answer == default_config.no_answer_message
    assert mock_llm.call_count == 0


@pytest.mark.asyncio
async def test_conflict_disclosure_sets_flag_and_system_message(
    default_config: AnswerGenerationConfig,
    mock_llm: MockLLM,
) -> None:
    conflict = ConflictGroup(
        entity_tag="paracetamol",
        attribute="max_daily_dose",
        item_ids=["ei_aaaa000000000001", "ei_bbbb000000000002"],
    )
    context = make_two_block_context().model_copy(
        update={"conflicts": [conflict]}
    )
    mock_llm.response = json.dumps(
        {
            "answer": (
                "Sources differ on dosing. Adults: 500 mg [ei_aaaa000000000001]."
            ),
            "confidence_note": None,
        }
    )
    pipeline = _pipeline(mock_llm)

    result = await pipeline.run(
        context=context,
        question="What is the dose?",
        config=default_config,
    )

    assert result.conflicts_disclosed is True
    assert mock_llm.last_chat_history is not None
    system_content = mock_llm.last_chat_history[0]["content"]
    assert default_config.conflict_disclosure_header in system_content


@pytest.mark.asyncio
async def test_empty_conflicts_not_disclosed(
    default_config: AnswerGenerationConfig,
    sample_context,
    mock_llm: MockLLM,
) -> None:
    pipeline = _pipeline(mock_llm)
    result = await pipeline.run(
        context=sample_context,
        question="What is the adult dose?",
        config=default_config,
    )
    assert result.conflicts_disclosed is False


@pytest.mark.asyncio
async def test_grounding_flag_emitted_answer_still_returned(
    default_config: AnswerGenerationConfig,
    mock_llm: MockLLM,
) -> None:
    context = make_context(
        blocks=[
            make_block(
                item_id="ei_aaaa000000000001",
                text="Metformin is used for type 2 diabetes.",
            )
        ]
    )
    mock_llm.response = json.dumps(
        {
            "answer": "The patient should take Metformin XR daily.",
            "confidence_note": None,
        }
    )
    pipeline = _pipeline(mock_llm)

    result = await pipeline.run(
        context=context,
        question="What should the patient take?",
        config=default_config,
    )

    assert result.answer
    assert any(flag.entity == "Metformin XR" for flag in result.grounding_flags)


@pytest.mark.asyncio
async def test_grounding_check_disabled_returns_no_flags(
    default_config: AnswerGenerationConfig,
    mock_llm: MockLLM,
) -> None:
    context = make_context(
        blocks=[
            make_block(
                item_id="ei_aaaa000000000001",
                text="Metformin is used for type 2 diabetes.",
            )
        ]
    )
    mock_llm.response = json.dumps(
        {"answer": "The patient should take Metformin XR daily.", "confidence_note": None}
    )
    config = default_config.model_copy(update={"grounding_check_enabled": False})
    pipeline = _pipeline(mock_llm, grounding_checker=EntityTagGroundingChecker())

    result = await pipeline.run(
        context=context,
        question="Question?",
        config=config,
    )

    assert result.grounding_flags == []


@pytest.mark.asyncio
async def test_structured_logging_includes_required_fields(
    default_config: AnswerGenerationConfig,
    sample_context,
    mock_llm: MockLLM,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="core.answer_generation.pipeline")
    pipeline = _pipeline(mock_llm)

    await pipeline.run(
        context=sample_context,
        question="What is the adult dose?",
        config=default_config,
    )

    messages = " ".join(record.message for record in caplog.records)
    assert "answer_generation_start" in messages
    assert "answer_generation_end" in messages
    assert "plan_id=plan_test001" in messages
    assert "context_id=ctx_test0000000001" in messages
    assert "provider=MockLLM" in messages
    assert "no_answer=false" in messages
