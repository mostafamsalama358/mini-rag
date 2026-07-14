"""Unit tests for SectionPathStitcher."""

from __future__ import annotations

import pytest

from core.context_builder.stitching.section_path_stitcher import SectionPathStitcher, _sort_key
from core.evidence_orchestrator.models import EvidenceItem
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from tests.unit.core.context_builder.conftest import make_item


@pytest.fixture
def stitcher() -> SectionPathStitcher:
    return SectionPathStitcher()


@pytest.fixture
def counter() -> CharacterApproximationTokenCounter:
    return CharacterApproximationTokenCounter()


@pytest.mark.asyncio
async def test_two_docs_produce_contiguous_doc_blocks(stitcher, counter):
    items = [
        (make_item(doc_id="docA", section_path=["Results"], relevance_score=0.5), "a", False),
        (make_item(doc_id="docA", section_path=["Introduction"], relevance_score=0.9, chunk_id="c2"), "b", False),
        (make_item(doc_id="docB", section_path=["Summary"], relevance_score=0.7, chunk_id="c3"), "c", False),
    ]
    blocks = await stitcher.stitch(items, counter)
    doc_ids = [block.document_id for block in blocks]
    assert doc_ids.index("docA") < doc_ids.index("docB")


@pytest.mark.asyncio
async def test_within_doc_introduction_before_results(stitcher, counter):
    items = [
        (make_item(doc_id="docA", section_path=["Results"], relevance_score=0.5), "results", False),
        (make_item(doc_id="docA", section_path=["Introduction"], relevance_score=0.9, chunk_id="c2"), "intro", False),
    ]
    blocks = await stitcher.stitch(items, counter)
    assert blocks[0].section_path == "Introduction"
    assert blocks[1].section_path == "Results"


@pytest.mark.asyncio
async def test_empty_section_path_sorts_after_non_empty(stitcher, counter):
    items = [
        (make_item(doc_id="docA", section_path=[], relevance_score=0.9), "empty", False),
        (make_item(doc_id="docA", section_path=["Intro"], relevance_score=0.5, chunk_id="c2"), "intro", False),
    ]
    blocks = await stitcher.stitch(items, counter)
    assert blocks[0].section_path == "Intro"
    assert blocks[1].section_path is None


@pytest.mark.asyncio
async def test_no_document_id_appears_last():
    has_doc = make_item(doc_id="docA", section_path=["B"], relevance_score=0.5, chunk_id="c2")
    no_doc = make_item(doc_id="docZ", section_path=["A"], relevance_score=0.9, chunk_id="c1")
    no_doc = EvidenceItem.model_construct(**{**no_doc.model_dump(), "doc_id": ""})
    key_has = _sort_key((has_doc, "has doc", False))
    key_no = _sort_key((no_doc, "no doc", False))
    assert key_has < key_no


@pytest.mark.asyncio
async def test_len_result_equals_len_input(stitcher, counter):
    items = [
        (make_item(chunk_id=f"c{i}"), f"text {i}", False)
        for i in range(4)
    ]
    blocks = await stitcher.stitch(items, counter)
    assert len(blocks) == len(items)


@pytest.mark.asyncio
async def test_section_path_joined_or_none(stitcher, counter):
    item = make_item(section_path=["Introduction", "Background"])
    blocks = await stitcher.stitch([(item, item.text, False)], counter)
    assert blocks[0].section_path == "Introduction/Background"


@pytest.mark.asyncio
async def test_compressed_flag_passed_through(stitcher, counter):
    item = make_item()
    blocks = await stitcher.stitch([(item, "compressed text", True)], counter)
    assert blocks[0].compressed is True
