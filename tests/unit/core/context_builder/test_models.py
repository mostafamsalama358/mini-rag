"""Unit tests for Context Builder domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.context_builder.config import BudgetReservations, ContextBuilderConfig
from core.context_builder.models import (
    ConflictGroup,
    Context,
    ContextBlock,
    ContextMetadata,
    compute_context_id,
)
from core.evidence_orchestrator.models import Citation
from tests.unit.core.context_builder.conftest import _citation, make_item


def test_context_citation_completeness_validator_raises():
    citation = _citation()
    item = make_item()
    metadata = ContextMetadata(
        items_included=1,
        items_dropped=0,
        items_compressed=0,
        budget_total=1000,
        budget_used=10,
    )
    with pytest.raises(ValidationError):
        Context(
            context_id=compute_context_id("ep_test", "2026-07-14T00:00:00Z"),
            pack_id="ep_test",
            plan_id="rp_test",
            ordered_blocks=[
                ContextBlock(
                    item_id=item.item_id,
                    document_id=item.doc_id,
                    text=item.text,
                    token_count=10,
                )
            ],
            citation_map={},
            token_count=10,
            metadata=metadata,
            created_at="2026-07-14T00:00:00Z",
        )


def test_context_token_count_sum_invariant():
    citation = _citation()
    item = make_item()
    metadata = ContextMetadata(
        items_included=1,
        items_dropped=0,
        items_compressed=0,
        budget_total=1000,
        budget_used=99,
    )
    with pytest.raises(ValidationError):
        Context(
            context_id=compute_context_id("ep_test", "2026-07-14T00:00:00Z"),
            pack_id="ep_test",
            plan_id="rp_test",
            ordered_blocks=[
                ContextBlock(
                    item_id=item.item_id,
                    document_id=item.doc_id,
                    text=item.text,
                    token_count=10,
                )
            ],
            citation_map={item.item_id: citation},
            token_count=99,
            metadata=metadata,
            created_at="2026-07-14T00:00:00Z",
        )


def test_empty_pack_context_construction():
    metadata = ContextMetadata(
        items_included=0,
        items_dropped=0,
        items_compressed=0,
        budget_total=6300,
        budget_used=0,
    )
    ctx = Context(
        context_id=compute_context_id("ep_empty", "2026-07-14T00:00:00Z"),
        pack_id="ep_empty",
        plan_id="rp_test",
        ordered_blocks=[],
        citation_map={},
        token_count=0,
        metadata=metadata,
        created_at="2026-07-14T00:00:00Z",
    )
    assert ctx.ordered_blocks == []
    assert ctx.citation_map == {}


def test_conflict_group_resolution_accepts_none_and_budget_drop():
    ConflictGroup(
        entity_tag="metformin",
        attribute="metformin:numeric",
        item_ids=["ei_a", "ei_b"],
        resolution=None,
    )
    ConflictGroup(
        entity_tag="metformin",
        attribute="metformin:numeric",
        item_ids=["ei_a", "ei_b"],
        resolution="budget_drop",
    )


def test_available_budget_computed_property():
    config = ContextBuilderConfig(
        total_context_window=8000,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
    )
    assert config.available_budget == 6300
