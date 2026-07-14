"""Evidence Orchestrator configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"
_WEIGHT_TOLERANCE = 0.001


class FusionWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieval: float = 0.6
    entity: float = 0.3
    recency: float = 0.1

    @model_validator(mode="after")
    def _sum_to_one(self) -> FusionWeights:
        total = self.retrieval + self.entity + self.recency
        if abs(total - 1.0) > _WEIGHT_TOLERANCE:
            raise ValueError(f"fusion_weights must sum to 1.0 (±{_WEIGHT_TOLERANCE})")
        return self


class CompressibilityWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    redundancy: float = 0.6
    relevance_inverse: float = 0.4

    @model_validator(mode="after")
    def _sum_to_one(self) -> CompressibilityWeights:
        total = self.redundancy + self.relevance_inverse
        if abs(total - 1.0) > _WEIGHT_TOLERANCE:
            raise ValueError(
                f"compressibility_weights must sum to 1.0 (±{_WEIGHT_TOLERANCE})"
            )
        return self


class EvidenceOrchestratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dedup_exact_enabled: bool = True
    dedup_near_enabled: bool = True
    dedup_similarity_threshold: float = Field(default=0.95, gt=0.0, le=1.0)
    dedup_near_batch_limit: int = Field(default=200, ge=1)
    expansion_enabled: bool = True
    expansion_score_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    expansion_min_chars: int = Field(default=150, ge=1)
    fusion_weights: FusionWeights = Field(default_factory=FusionWeights)
    compressibility_weights: CompressibilityWeights = Field(
        default_factory=CompressibilityWeights
    )
    token_counter: str = "character"
    celery_offload_threshold: int = Field(default=500, ge=1)
    schema_version: str = SCHEMA_VERSION


def load_config_from_yaml(path: Path) -> EvidenceOrchestratorConfig:
    """Load EvidenceOrchestratorConfig from a field-pack YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    return EvidenceOrchestratorConfig.model_validate(data)


def merge_config(
    base: EvidenceOrchestratorConfig,
    override: dict[str, Any] | EvidenceOrchestratorConfig | None,
) -> EvidenceOrchestratorConfig:
    """Merge generic < domain < project overrides."""
    if override is None:
        return base
    if isinstance(override, EvidenceOrchestratorConfig):
        merged = {**base.model_dump(), **override.model_dump(exclude_unset=True)}
    else:
        merged = _deep_merge(base.model_dump(), override)
    return EvidenceOrchestratorConfig.model_validate(merged)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
