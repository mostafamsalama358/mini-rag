"""Static capability declarations for infrastructure adapters (spec 015)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterCapabilities:
    """Fail-fast startup validation set for a retriever adapter."""

    retriever_id: str
    supported_strategy: str
    features: frozenset[str]
