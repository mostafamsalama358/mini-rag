"""Answer Generation configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from core.answer_generation.models import CapabilityModule

SCHEMA_VERSION = "1.0.0"

_FIELDS_DIR = Path(__file__).resolve().parent.parent.parent / "fields"


class AnswerGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_schema_version: str = "1.0.0"
    max_output_tokens: int = Field(default=2048, ge=1)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    grounding_check_enabled: bool = True
    no_answer_message: str = Field(
        default="The answer could not be found in the provided sources.",
        min_length=1,
    )
    conflict_disclosure_header: str = Field(
        default="## Conflicting Information",
        min_length=1,
    )
    system_prompt_template: str = Field(min_length=1)
    capability_modules: list[CapabilityModule] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


def load_config_from_yaml(path: Path) -> AnswerGenerationConfig:
    """Load AnswerGenerationConfig from a field-pack YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    return AnswerGenerationConfig.model_validate(data)


def merge_config(
    base: AnswerGenerationConfig,
    override: dict[str, Any] | AnswerGenerationConfig | None,
) -> AnswerGenerationConfig:
    """Merge generic < domain < project overrides."""
    if override is None:
        return base
    if isinstance(override, AnswerGenerationConfig):
        merged = {**base.model_dump(), **override.model_dump(exclude_unset=True)}
    else:
        merged = _deep_merge(base.model_dump(), override)
    return AnswerGenerationConfig.model_validate(merged)


def resolve_answer_generation_config(
    domain_key: str,
    project_overrides: dict[str, Any] | None = None,
) -> AnswerGenerationConfig:
    """Load and merge answer_generation config: generic < domain < project."""
    generic_path = _FIELDS_DIR / "generic" / "answer_generation.yaml"
    domain_path = _FIELDS_DIR / domain_key / "answer_generation.yaml"

    base = load_config_from_yaml(generic_path)
    if domain_path.exists() and domain_key != "generic":
        domain_cfg = load_config_from_yaml(domain_path)
        base = merge_config(base, domain_cfg)

    if project_overrides:
        ag_override = project_overrides.get("answer_generation")
        if isinstance(ag_override, dict):
            base = merge_config(base, ag_override)

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
