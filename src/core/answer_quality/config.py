"""Answer Quality configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from core.answer_quality.models import ScoreThresholds

SCHEMA_VERSION = "1.0.0"

_FIELDS_DIR = Path(__file__).resolve().parent.parent.parent / "fields"


class AnswerQualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_thresholds: ScoreThresholds = Field(default_factory=ScoreThresholds)
    pass_rate_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    regression_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    completeness_overlap_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    run_store_dir: str = ".answer_quality/runs"
    fixture_dir: str = "tests/fixtures/answer_quality"
    schema_version: str = SCHEMA_VERSION


def load_config_from_yaml(path: Path) -> AnswerQualityConfig:
    """Load AnswerQualityConfig from a field-pack YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    return AnswerQualityConfig.model_validate(data)


def merge_config(
    base: AnswerQualityConfig,
    override: dict[str, Any] | AnswerQualityConfig | None,
) -> AnswerQualityConfig:
    """Merge generic < domain < project overrides."""
    if override is None:
        return base
    if isinstance(override, AnswerQualityConfig):
        merged = {**base.model_dump(), **override.model_dump(exclude_unset=True)}
    else:
        merged = _deep_merge(base.model_dump(), override)
    return AnswerQualityConfig.model_validate(merged)


def resolve_answer_quality_config(
    domain_key: str,
    project_overrides: dict[str, Any] | None = None,
) -> AnswerQualityConfig:
    """Load and merge answer_quality config: generic < domain < project."""
    generic_path = _FIELDS_DIR / "generic" / "answer_quality.yaml"
    domain_path = _FIELDS_DIR / domain_key / "answer_quality.yaml"

    base = load_config_from_yaml(generic_path)
    if domain_path.exists() and domain_key != "generic":
        domain_cfg = load_config_from_yaml(domain_path)
        base = merge_config(base, domain_cfg)

    if project_overrides:
        aq_override = project_overrides.get("answer_quality")
        if isinstance(aq_override, dict):
            base = merge_config(base, aq_override)

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
