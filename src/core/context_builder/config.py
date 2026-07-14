"""Context Builder configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"

_FIELDS_DIR = Path(__file__).resolve().parent.parent.parent / "fields"


class BudgetReservations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: int = 500
    question: int = 200
    output: int = 1000


class ContextBuilderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_context_window: int = Field(default=8000, ge=1)
    reservations: BudgetReservations = Field(default_factory=BudgetReservations)
    compressibility_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    final_dedup_enabled: bool = True
    final_dedup_similarity_threshold: float = Field(default=0.85, gt=0.0, le=1.0)
    final_dedup_max_pairs: int = Field(default=2000, ge=1)
    compression_enabled: bool = True
    compression_strategy: str = "heuristic"
    token_counter: str = "character"
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    evidence_pack_schema_version: str = "1.0.0"
    schema_version: str = SCHEMA_VERSION

    @property
    def available_budget(self) -> int:
        return max(
            0,
            self.total_context_window
            - self.reservations.system_prompt
            - self.reservations.question
            - self.reservations.output,
        )


def load_config_from_yaml(path: Path) -> ContextBuilderConfig:
    """Load ContextBuilderConfig from a field-pack YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    return ContextBuilderConfig.model_validate(data)


def merge_config(
    base: ContextBuilderConfig,
    override: dict[str, Any] | ContextBuilderConfig | None,
) -> ContextBuilderConfig:
    """Merge generic < domain < project overrides."""
    if override is None:
        return base
    if isinstance(override, ContextBuilderConfig):
        merged = {**base.model_dump(), **override.model_dump(exclude_unset=True)}
    else:
        merged = _deep_merge(base.model_dump(), override)
    return ContextBuilderConfig.model_validate(merged)


def resolve_context_builder_config(
    domain_key: str,
    project_overrides: dict[str, Any] | None = None,
) -> ContextBuilderConfig:
    """Load and merge context_builder config: generic < domain < project."""
    generic_path = _FIELDS_DIR / "generic" / "context_builder.yaml"
    domain_path = _FIELDS_DIR / domain_key / "context_builder.yaml"

    base = load_config_from_yaml(generic_path)
    if domain_path.exists() and domain_key != "generic":
        domain_cfg = load_config_from_yaml(domain_path)
        base = merge_config(base, domain_cfg)

    if project_overrides:
        cb_override = project_overrides.get("context_builder")
        if isinstance(cb_override, dict):
            base = merge_config(base, cb_override)

    return base


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
