"""Unit tests for EntityHintExpander."""

from __future__ import annotations

from core.retrieval_engine.expansion.entity_hint import EntityHintExpander
from core.retrieval_engine.models import ExpansionContext


def test_entity_hint_adds_entity_variant() -> None:
    expander = EntityHintExpander()
    result = expander.expand(
        ExpansionContext(
            query_text="What is the adult dose of aspirin?",
            entities=("aspirin",),
            max_variants=3,
        )
    )
    assert result.variants[0] == "What is the adult dose of aspirin?"
    assert any("aspirin" in v.lower() for v in result.variants[1:])
    assert len(result.variants) >= 2


def test_passthrough_when_no_entities() -> None:
    expander = EntityHintExpander()
    result = expander.expand(
        ExpansionContext(query_text="hello world", entities=(), max_variants=3)
    )
    assert result.variants == ("hello world",)
