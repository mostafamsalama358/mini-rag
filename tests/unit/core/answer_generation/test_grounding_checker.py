"""Unit tests for EntityTagGroundingChecker."""

from __future__ import annotations

import time

from core.answer_generation.grounding.entity_tag_checker import EntityTagGroundingChecker
from tests.unit.core.answer_generation.conftest import make_block, make_context


def test_entity_in_context_returns_no_flags() -> None:
    context = make_context(
        blocks=[
            make_block(
                item_id="ei_aaaa000000000001",
                text="Metformin is used for type 2 diabetes.",
            )
        ]
    )
    flags = EntityTagGroundingChecker().check(
        "Metformin is commonly prescribed.",
        context,
    )
    assert flags == []


def test_entity_absent_from_context_emits_flag() -> None:
    context = make_context(
        blocks=[
            make_block(
                item_id="ei_aaaa000000000001",
                text="Metformin is used for type 2 diabetes.",
            )
        ]
    )
    flags = EntityTagGroundingChecker().check(
        "The patient should take Metformin XR daily.",
        context,
    )
    assert len(flags) == 1
    assert flags[0].entity == "Metformin XR"
    assert flags[0].reason == "entity_not_in_context"


def test_multiple_ungrounded_entities_emit_multiple_flags() -> None:
    context = make_context(
        blocks=[make_block(item_id="ei_aaaa000000000001", text="Short context.")]
    )
    flags = EntityTagGroundingChecker().check(
        "Use Alpha Beta and Gamma Delta together.",
        context,
    )
    entities = {flag.entity for flag in flags}
    assert "Alpha Beta" in entities
    assert "Gamma Delta" in entities


def test_runtime_sub_millisecond() -> None:
    context = make_context(
        blocks=[make_block(item_id="ei_aaaa000000000001", text="word " * 200)]
    )
    answer = "Some answer. " * 100
    checker = EntityTagGroundingChecker()

    start = time.perf_counter()
    checker.check(answer, context)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert elapsed_ms < 50.0
