"""Intelligent Chunking Engine public API (spec 007)."""

from core.chunking.interfaces import BoundaryDecisionPolicy, ChunkingStrategy
from core.chunking.models import (
    BoundaryDecision,
    BoundaryFeatures,
    ChunkingStrategyConfig,
    ChunkSet,
    ValidationReport,
    compute_config_hash,
)
from core.chunking.registry import (
    get_boundary_decision_policy,
    get_chunking_strategy,
    register_policy,
    register_strategy,
)

# Register built-in strategy and policy on import.
import core.chunking.strategies  # noqa: F401

__all__ = [
    "BoundaryDecision",
    "BoundaryDecisionPolicy",
    "BoundaryFeatures",
    "ChunkingStrategy",
    "ChunkingStrategyConfig",
    "ChunkSet",
    "ValidationReport",
    "compute_config_hash",
    "get_boundary_decision_policy",
    "get_chunking_strategy",
    "register_policy",
    "register_strategy",
]
