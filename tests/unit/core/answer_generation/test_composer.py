"""Unit tests for DefaultPromptComposer."""

from __future__ import annotations

from core.answer_generation.composition.default_composer import DefaultPromptComposer
from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.models import CapabilityModule
from tests.unit.core.answer_generation.conftest import make_two_block_context


def test_compose_preserves_block_order_and_markers(default_config: AnswerGenerationConfig) -> None:
    context = make_two_block_context()
    prompt = DefaultPromptComposer().compose(
        context,
        "What is the adult dose?",
        default_config,
    )

    first_idx = prompt.user_message.index("[ei_aaaa000000000001]")
    second_idx = prompt.user_message.index("[ei_bbbb000000000002]")
    assert first_idx < second_idx
    assert "What is the adult dose?" in prompt.user_message
    assert default_config.system_prompt_template in prompt.system_message
    assert prompt.has_conflict_disclosure is False


def test_compose_leaves_conflict_disclosure_false(
    default_config: AnswerGenerationConfig,
) -> None:
    context = make_two_block_context()
    prompt = DefaultPromptComposer().compose(context, "Question?", default_config)
    assert prompt.has_conflict_disclosure is False


def test_compose_sorts_capability_modules_by_priority(
    default_config: AnswerGenerationConfig,
) -> None:
    context = make_two_block_context()
    config = default_config.model_copy(
        update={
            "capability_modules": [
                CapabilityModule(name="low", instructions="Second", priority=10),
                CapabilityModule(name="high", instructions="First", priority=0),
            ]
        }
    )
    prompt = DefaultPromptComposer().compose(context, "Question?", config)

    high_idx = prompt.system_message.index("Domain Module: high")
    low_idx = prompt.system_message.index("Domain Module: low")
    assert high_idx < low_idx
    assert prompt.module_names == ["high", "low"]
