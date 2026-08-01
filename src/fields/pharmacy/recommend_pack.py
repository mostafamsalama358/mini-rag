"""Load pharmacy recommend pack YAML artifacts (Feature 020)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PACK_DIR = Path(__file__).resolve().parent


def _load_yaml(name: str) -> dict[str, Any]:
    path = _PACK_DIR / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Recommend pack file must be a mapping: {path}")
    return data


@lru_cache(maxsize=1)
def load_symptom_taxonomy() -> dict[str, Any]:
    return _load_yaml("symptom_taxonomy.yaml")


@lru_cache(maxsize=1)
def load_recommendation_policy() -> dict[str, Any]:
    return _load_yaml("recommendation_policy.yaml")


@lru_cache(maxsize=1)
def load_safety_model() -> dict[str, Any]:
    return _load_yaml("safety_model.yaml")


@lru_cache(maxsize=1)
def load_indication_tags() -> dict[str, Any]:
    return _load_yaml("indication_tags.yaml")


def list_recommend_pack_files() -> list[str]:
    """Discovery helper for FieldRegistry / docs (T012)."""
    names = [
        "symptom_taxonomy.yaml",
        "recommendation_policy.yaml",
        "safety_model.yaml",
        "indication_tags.yaml",
    ]
    return [n for n in names if (_PACK_DIR / n).exists()]


def clear_recommend_pack_cache() -> None:
    load_symptom_taxonomy.cache_clear()
    load_recommendation_policy.cache_clear()
    load_safety_model.cache_clear()
    load_indication_tags.cache_clear()
