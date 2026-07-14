"""US5: assembler / representation strategy tests."""

from __future__ import annotations

from core.chunking.models import ChunkSet
from core.knowledge.models import KnowledgeExtractionConfig
from core.knowledge.pipeline import build_pipeline_from_config
from core.knowledge.registry import register_defaults
from core.knowledge.representation.base import (
    StubGraphRepresentationStrategy,
    StubRelationalRepresentationStrategy,
)
from tests.unit.core.knowledge.conftest import assert_package_unchanged


def test_representation_strategy_no_mutation(chunk_set_five_forms: ChunkSet) -> None:
    register_defaults()
    config = KnowledgeExtractionConfig(
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
        representation_strategies=["stub_graph", "stub_relational"],
    )
    pipeline = build_pipeline_from_config(config)
    package = pipeline.run(chunk_set_five_forms, config)
    before = package
    graph = StubGraphRepresentationStrategy().apply(package)
    relational = StubRelationalRepresentationStrategy().apply(package)
    assert_package_unchanged(before, package)
    assert "nodes" in graph and "edges" in graph
    assert isinstance(relational, list)
    assert len(pipeline.last_representation_artifacts) == 2


def test_idempotent_reprocessing(chunk_set_five_forms: ChunkSet) -> None:
    config = KnowledgeExtractionConfig(
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
    )
    pipeline = build_pipeline_from_config(config)
    first = pipeline.run(chunk_set_five_forms, config)
    second = pipeline.run(chunk_set_five_forms, config)
    assert first.metadata.package_id == second.metadata.package_id
    assert [u.id for u in first.knowledge_units] == [
        u.id for u in second.knowledge_units
    ]


def test_no_graph_generated_when_not_configured(
    chunk_set_five_forms: ChunkSet,
) -> None:
    config = KnowledgeExtractionConfig(
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
        representation_strategies=[],
    )
    pipeline = build_pipeline_from_config(config)
    package = pipeline.run(chunk_set_five_forms, config)
    assert package.validation_report is not None
    assert pipeline.last_representation_artifacts == []
