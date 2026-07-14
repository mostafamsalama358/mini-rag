"""Unit tests for JsonOutputParser."""

from __future__ import annotations

import json

import pytest

from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.errors import AnswerGenerationError
from core.answer_generation.parsing.json_output_parser import JsonOutputParser


def test_json_parse_success(default_config: AnswerGenerationConfig) -> None:
    raw = json.dumps({"answer": "Hello", "confidence_note": "Sure"})
    answer, note = JsonOutputParser().parse(raw, default_config)
    assert answer == "Hello"
    assert note == "Sure"


def test_json_parse_failure_falls_back_to_plain_text(
    default_config: AnswerGenerationConfig,
) -> None:
    raw = "Plain answer text."
    answer, note = JsonOutputParser().parse(raw, default_config)
    assert answer == "Plain answer text."
    assert note is None


def test_empty_response_signals_no_answer(default_config: AnswerGenerationConfig) -> None:
    answer, note = JsonOutputParser().parse('{"answer": ""}', default_config)
    assert answer == ""
    assert note is None


def test_unparseable_json_answer_type_raises(default_config: AnswerGenerationConfig) -> None:
    with pytest.raises(AnswerGenerationError, match="not a string"):
        JsonOutputParser().parse('{"answer": 42}', default_config)
