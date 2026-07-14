"""Knowledge Representation pipeline orchestrator and config loading."""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from core.chunking.models import ChunkSet
from core.knowledge.assembly import KnowledgePackageAssembler
from core.knowledge.errors import KnowledgeValidationFailedError
from core.knowledge.interfaces import (
    KnowledgeNormalizer,
    KnowledgeRepresentationStrategy,
    KnowledgeUnitExtractor,
    RelationshipDiscoverer,
)
from core.knowledge.models import KnowledgeExtractionConfig, KnowledgePackage
from core.knowledge.registry import (
    discoverer_registry,
    extractor_registry,
    get_discoverer,
    get_extractor,
    get_normalizer,
    get_representation_strategy,
    normalizer_registry,
    register_defaults,
    representation_strategy_registry,
)
from core.knowledge.validation import KnowledgeValidator

logger = logging.getLogger(__name__)

_FIELDS_DIR = Path(__file__).resolve().parent.parent.parent / "fields"


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    if not override:
        return deepcopy(base)
    merged = deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _load_yaml_section(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    section = data.get("knowledge_representation", data)
    return section if isinstance(section, dict) else {}


def load_knowledge_extraction_config(
    *,
    domain: str = "generic",
    project_overrides: dict[str, Any] | None = None,
    fields_dir: Path | None = None,
) -> KnowledgeExtractionConfig:
    """Load KnowledgeExtractionConfig with generic < domain < project precedence."""
    root = fields_dir or _FIELDS_DIR
    generic = _load_yaml_section(root / "generic" / "knowledge_representation.yaml")
    domain_data = (
        {}
        if domain == "generic"
        else _load_yaml_section(root / domain / "knowledge_representation.yaml")
    )
    merged = _deep_merge(generic, domain_data)
    if project_overrides:
        kr = project_overrides.get("knowledge_representation", project_overrides)
        if isinstance(kr, dict):
            merged = _deep_merge(merged, kr)
    return KnowledgeExtractionConfig.model_validate(merged)


class KnowledgeRepresentationPipeline:
    """Six-stage Knowledge Representation orchestrator."""

    def __init__(
        self,
        extractor: KnowledgeUnitExtractor,
        normalizer: KnowledgeNormalizer,
        discoverer: RelationshipDiscoverer,
        representation_strategies: list[KnowledgeRepresentationStrategy],
        validator: KnowledgeValidator,
        assembler: KnowledgePackageAssembler,
    ) -> None:
        self.extractor = extractor
        self.normalizer = normalizer
        self.discoverer = discoverer
        self.representation_strategies = list(representation_strategies)
        self.validator = validator
        self.assembler = assembler
        self.last_representation_artifacts: list[Any] = []

    def run(
        self,
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> KnowledgePackage:
        # 1. Extraction
        raw_units = self.extractor.extract(chunk_set, config)
        # 2. Normalization
        normalized = self.normalizer.normalize(raw_units, config)
        # 3. Relationship candidates
        candidates = self.discoverer.generate_candidates(normalized, chunk_set, config)
        # 4. Relationship validation
        relationships = self.discoverer.validate_candidates(
            candidates, normalized, config
        )
        # 5. Assembly (draft)
        draft = self.assembler.assemble(
            normalized,
            relationships,
            config,
            chunk_set,
            extractor_strategy_id=self.extractor.strategy_id,
            normalizer_strategy_id=self.normalizer.strategy_id,
            discoverer_strategy_id=self.discoverer.strategy_id,
        )
        # 6. Validation
        document_model_id = draft.metadata.document_model_id
        report = self.validator.validate(
            draft, chunk_set, document_model_id, max_units=config.max_units
        )
        final_package = self.assembler.assemble(
            list(draft.knowledge_units),
            list(draft.knowledge_relationships),
            config,
            chunk_set,
            extractor_strategy_id=self.extractor.strategy_id,
            normalizer_strategy_id=self.normalizer.strategy_id,
            discoverer_strategy_id=self.discoverer.strategy_id,
            validation_report=report,
        )

        if config.fail_on_error and report.status == "failed":
            raise KnowledgeValidationFailedError(
                f"Knowledge validation failed with {len(report.errors)} error(s)"
            )

        # Optional representation strategies (read-only; package unchanged)
        before = final_package
        self.last_representation_artifacts = []
        for strategy in self.representation_strategies:
            artifact = strategy.apply(final_package)
            self.last_representation_artifacts.append(artifact)
        assert final_package is before

        logger.info(
            "knowledge_pipeline_complete asset_id=%s package_id=%s units=%s "
            "relationships=%s status=%s",
            chunk_set.asset_id,
            final_package.metadata.package_id,
            len(final_package.knowledge_units),
            len(final_package.knowledge_relationships),
            final_package.validation_report.status,
        )
        return final_package


def build_pipeline_from_config(
    config: KnowledgeExtractionConfig,
    *,
    registries: dict[str, Any] | None = None,
) -> KnowledgeRepresentationPipeline:
    """Factory: resolve strategies from registries with no if/else on names."""
    register_defaults()
    if registries:
        extractor = registries["extractor"].get(config.extractor_strategy)
        normalizer = registries["normalizer"].get(config.normalizer_strategy)
        discoverer = registries["discoverer"].get(config.discoverer_strategy)
        rep_reg = registries.get("representation", representation_strategy_registry)
    else:
        extractor = get_extractor(config.extractor_strategy)
        normalizer = get_normalizer(config.normalizer_strategy)
        discoverer = get_discoverer(config.discoverer_strategy)
        rep_reg = representation_strategy_registry

    representation_strategies = [
        rep_reg.get(name) if hasattr(rep_reg, "get") else get_representation_strategy(name)
        for name in config.representation_strategies
    ]
    return KnowledgeRepresentationPipeline(
        extractor=extractor,
        normalizer=normalizer,
        discoverer=discoverer,
        representation_strategies=representation_strategies,  # type: ignore[arg-type]
        validator=KnowledgeValidator(),
        assembler=KnowledgePackageAssembler(),
    )


# Re-export registries for callers that wire manually.
__all__ = [
    "KnowledgeRepresentationPipeline",
    "build_pipeline_from_config",
    "load_knowledge_extraction_config",
    "extractor_registry",
    "normalizer_registry",
    "discoverer_registry",
    "representation_strategy_registry",
]
