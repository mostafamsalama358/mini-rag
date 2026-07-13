"""Auto-register default chunking strategy and boundary decision policy."""

from core.chunking.registry import register_policy, register_strategy
from core.chunking.strategies.semantic_structural import (
    RuleBasedBoundaryDecisionPolicy,
    SemanticStructuralChunkingStrategy,
)

register_strategy("semantic_structural", SemanticStructuralChunkingStrategy)
register_policy("rule_based", RuleBasedBoundaryDecisionPolicy)
