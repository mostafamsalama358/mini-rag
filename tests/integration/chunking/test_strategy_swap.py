"""US2: strategy-based swappable chunking architecture."""

from __future__ import annotations

import core.chunking.strategies  # noqa: F401
from core.chunking.models import BoundaryCandidate, BoundaryDecision, BoundaryFeatures, ChunkingStrategyConfig
from core.chunking.registry import get_chunking_strategy, register_policy, register_strategy
from core.chunking.strategies.semantic_structural import SemanticStructuralChunkingStrategy
from fields.schemas import ChunkingProfile
from tests.fixtures.chunking.heading_table_sections import FIXTURE_DOC
from tests.integration.chunking.fixtures.passthrough_strategy import PassthroughChunkingStrategy


def _records(chunk_set):
    return [{"text": c.text, "metadata": c.metadata} for c in chunk_set.chunks]


def test_default_strategy():
    config = ChunkingStrategyConfig()
    strategy = get_chunking_strategy("semantic_structural", config)
    chunk_set = strategy.chunk(FIXTURE_DOC, config)
    assert chunk_set.strategy_id == "semantic_structural"
    assert chunk_set.chunks
    assert chunk_set.validation_report.status in ("pass", "pass_with_warnings", "fail")


def test_passthrough_strategy():
    register_strategy("passthrough", PassthroughChunkingStrategy)
    config = ChunkingStrategyConfig(strategy="passthrough")
    strategy = get_chunking_strategy("passthrough", config)
    chunk_set = strategy.chunk(FIXTURE_DOC, config)
    assert len(chunk_set.chunks) == len(FIXTURE_DOC.elements)


def test_downstream_contract_unchanged():
    register_strategy("passthrough", PassthroughChunkingStrategy)
    default = _records(
        get_chunking_strategy("semantic_structural", ChunkingStrategyConfig()).chunk(
            FIXTURE_DOC, ChunkingStrategyConfig()
        )
    )
    passthrough = _records(
        get_chunking_strategy("passthrough", ChunkingStrategyConfig(strategy="passthrough")).chunk(
            FIXTURE_DOC, ChunkingStrategyConfig(strategy="passthrough")
        )
    )
    required = {"text", "metadata", "element_type", "source_element_ids", "char_count"}
    for rec in default + passthrough:
        assert "text" in rec
        meta = rec["metadata"]
        for key in ("element_type", "source_element_ids", "char_count"):
            assert key in meta


class FirstAlwaysSplitPolicy:
    def decide(self, candidate: BoundaryCandidate, features: BoundaryFeatures) -> BoundaryDecision:
        return BoundaryDecision(
            decision="split",
            applied_rule="always_split",
            triggered_features=["size_budget"],
            rationale="Test policy always splits",
        )


def test_policy_swap():
    register_policy("always_split", FirstAlwaysSplitPolicy)
    config = ChunkingStrategyConfig(policy="always_split")
    strategy = SemanticStructuralChunkingStrategy(config)
    chunk_set = strategy.chunk(FIXTURE_DOC, config)
    assert len(chunk_set.chunks) >= len(FIXTURE_DOC.elements) - 1


def test_yaml_driven_strategy_selection():
    profile = ChunkingProfile.model_validate(
        {"strategy": "passthrough", "policy": "rule_based", "chunk_size": 800}
    )
    register_strategy("passthrough", PassthroughChunkingStrategy)
    config = ChunkingStrategyConfig(
        strategy=profile.strategy,
        max_chars=profile.chunk_size,
        overlap=profile.overlap,
        policy=profile.policy,
        element_mapping=profile.element_mapping,
    )
    strategy = get_chunking_strategy(profile.strategy, config)
    assert isinstance(strategy, PassthroughChunkingStrategy)


def test_parallel_strategy_metadata_keys():
    register_strategy("passthrough", PassthroughChunkingStrategy)
    default_records = _records(
        get_chunking_strategy("semantic_structural", ChunkingStrategyConfig()).chunk(
            FIXTURE_DOC, ChunkingStrategyConfig()
        )
    )
    passthrough_records = _records(
        get_chunking_strategy("passthrough", ChunkingStrategyConfig(strategy="passthrough")).chunk(
            FIXTURE_DOC, ChunkingStrategyConfig(strategy="passthrough")
        )
    )
    default_keys = {k for rec in default_records for k in rec["metadata"]}
    passthrough_keys = {k for rec in passthrough_records for k in rec["metadata"]}
    assert default_keys == passthrough_keys
