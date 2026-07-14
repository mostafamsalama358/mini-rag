"""US2: registry dispatch tests."""

from __future__ import annotations

import pytest

from core.chunking.models import ChunkSet
from core.knowledge.errors import StrategyNotFoundError
from core.knowledge.models import KnowledgeExtractionConfig
from core.knowledge.pipeline import build_pipeline_from_config
from core.knowledge.registry import (
    extractor_registry,
    register_defaults,
)


def test_extractor_registry_dispatch() -> None:
    register_defaults()
    impl = extractor_registry.get("structural")
    assert impl.strategy_id == "structural"


def test_unknown_strategy_raises() -> None:
    register_defaults()
    with pytest.raises(StrategyNotFoundError):
        extractor_registry.get("does_not_exist")


def test_pipeline_uses_config_strategy(chunk_set_five_forms: ChunkSet) -> None:
    register_defaults()
    config = KnowledgeExtractionConfig(
        extractor_strategy="structural",
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
    )
    package = build_pipeline_from_config(config).run(chunk_set_five_forms, config)
    assert package.metadata.extractor_strategy_id == "structural"
    assert len(package.knowledge_units) == 5
