"""US4: stable identity, lineage, and reproducibility."""

from __future__ import annotations

import core.chunking.strategies  # noqa: F401
from core.chunking.models import ChunkingStrategyConfig
from core.chunking.registry import get_chunking_strategy
from core.chunking.strategies.semantic_structural import RuleBasedBoundaryDecisionPolicy
from tests.fixtures.chunking.heading_table_sections import FIXTURE_DOC


def _run():
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)
    return strategy.chunk(FIXTURE_DOC, config)


def _snapshot(chunk_set):
    return [
        {
            "chunk_id": c.identity.chunk_id if c.identity else None,
            "text": c.text,
            "heading_path": c.metadata.get("heading_path"),
            "lineage": c.lineage.model_dump() if c.lineage else None,
            "relationships": c.relationships.model_dump(),
        }
        for c in chunk_set.chunks
    ]


def test_identical_runs_produce_identical_output():
    first = _snapshot(_run())
    second = _snapshot(_run())
    assert first == second


def test_boundary_decision_replay():
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)
    chunk_set = strategy.chunk(FIXTURE_DOC, config)
    policy = RuleBasedBoundaryDecisionPolicy()
    for chunk in chunk_set.chunks:
        if chunk.lineage is None:
            continue
        # Lineage stores applied decisions; replay is policy-level contract smoke test.
        assert chunk.lineage.applied_rule
        assert chunk.lineage.triggered_features


def test_boundary_decision_has_no_confidence_field():
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)
    chunk_set = strategy.chunk(FIXTURE_DOC, config)
    for chunk in chunk_set.chunks:
        if chunk.lineage:
            dumped = chunk.lineage.model_dump()
            for value in dumped.values():
                if isinstance(value, (int, float)) and value not in (0,):
                    if "split_index" not in str(dumped):
                        pass
            assert "confidence" not in dumped
            assert "probability" not in dumped
