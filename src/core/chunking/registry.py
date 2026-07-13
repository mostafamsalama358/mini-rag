"""Strategy and policy registries with factory functions."""

from __future__ import annotations

from core.chunking.interfaces import BoundaryDecisionPolicy, ChunkingStrategy
from core.chunking.models import ChunkingStrategyConfig

_STRATEGY_REGISTRY: dict[str, type[ChunkingStrategy]] = {}
_POLICY_REGISTRY: dict[str, type] = {}


def register_strategy(name: str, cls: type[ChunkingStrategy]) -> None:
    if name in _STRATEGY_REGISTRY and _STRATEGY_REGISTRY[name] is not cls:
        raise ValueError(f"strategy '{name}' is already registered")
    _STRATEGY_REGISTRY[name] = cls


def get_chunking_strategy(name: str, config: ChunkingStrategyConfig) -> ChunkingStrategy:
    if name not in _STRATEGY_REGISTRY:
        raise KeyError(f"unknown chunking strategy: {name}")
    return _STRATEGY_REGISTRY[name](config=config)


def register_policy(name: str, cls: type) -> None:
    if name in _POLICY_REGISTRY and _POLICY_REGISTRY[name] is not cls:
        raise ValueError(f"policy '{name}' is already registered")
    _POLICY_REGISTRY[name] = cls


def get_boundary_decision_policy(name: str) -> BoundaryDecisionPolicy:
    if name not in _POLICY_REGISTRY:
        raise KeyError(f"unknown boundary decision policy: {name}")
    return _POLICY_REGISTRY[name]()
