"""Unit tests for HeuristicTruncationCompressor."""

from __future__ import annotations

import pytest

from core.context_builder.compression.heuristic_compressor import (
    HeuristicTruncationCompressor,
)
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from tests.unit.core.context_builder.conftest import make_item


@pytest.fixture
def compressor() -> HeuristicTruncationCompressor:
    return HeuristicTruncationCompressor()


@pytest.fixture
def counter() -> CharacterApproximationTokenCounter:
    return CharacterApproximationTokenCounter()


@pytest.mark.asyncio
async def test_compressed_text_within_target_tokens(compressor, counter):
    text = "First sentence here. Second sentence here. Third sentence here."
    item = make_item(text=text)
    compressed, tokens = await compressor.compress(item, target_tokens=8, token_counter=counter)
    assert compressed
    assert tokens <= 9


@pytest.mark.asyncio
async def test_non_empty_output_for_non_empty_input(compressor, counter):
    item = make_item(text="Hello world.")
    compressed, tokens = await compressor.compress(item, target_tokens=5, token_counter=counter)
    assert compressed
    assert tokens >= 1


@pytest.mark.asyncio
async def test_target_tokens_zero_returns_empty(compressor, counter):
    item = make_item(text="Hello world.")
    compressed, tokens = await compressor.compress(item, target_tokens=0, token_counter=counter)
    assert compressed == ""
    assert tokens == 0


@pytest.mark.asyncio
async def test_sentence_boundary_preserves_complete_sentences(compressor, counter):
    text = "Alpha sentence. Beta sentence. Gamma sentence."
    item = make_item(text=text)
    compressed, _ = await compressor.compress(item, target_tokens=6, token_counter=counter)
    assert compressed.endswith(".")
    assert "Alpha sentence." in compressed or compressed.startswith("Alpha")


@pytest.mark.asyncio
async def test_hard_truncation_fallback_when_no_boundary_fits(compressor, counter):
    text = "word " * 200
    item = make_item(text=text.strip())
    compressed, tokens = await compressor.compress(item, target_tokens=3, token_counter=counter)
    assert compressed
    assert tokens <= 3
