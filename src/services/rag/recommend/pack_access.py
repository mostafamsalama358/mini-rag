"""Domain-pack recommend loaders via dynamic import (no static fields.pharmacy)."""

from __future__ import annotations

from typing import Any

from services.rag.domain_helpers import call_domain_helper

_DEFAULT_DOMAIN = "pharmacy"


def load_recommendation_policy(domain_key: str = _DEFAULT_DOMAIN) -> dict[str, Any]:
    return call_domain_helper(domain_key, "recommend_pack", "load_recommendation_policy") or {}


def load_safety_model(domain_key: str = _DEFAULT_DOMAIN) -> dict[str, Any]:
    return call_domain_helper(domain_key, "recommend_pack", "load_safety_model") or {}


def load_indication_tags(domain_key: str = _DEFAULT_DOMAIN) -> dict[str, Any]:
    return call_domain_helper(domain_key, "recommend_pack", "load_indication_tags") or {}
