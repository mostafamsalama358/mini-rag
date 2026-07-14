"""Context Builder — budget-compliant EvidencePack → Context assembly."""

from core.context_builder.config import ContextBuilderConfig
from core.context_builder.interfaces import (
    IConflictDetector,
    IContextCompressor,
    IContextStitcher,
    ITokenBudgetAllocator,
)
from core.context_builder.models import (
    ConflictGroup,
    Context,
    ContextBlock,
    ContextMetadata,
)
from core.context_builder.pipeline import ContextBuilderPipeline
from core.context_builder.registry import ContextBuilderRegistry

__all__ = [
    "ConflictGroup",
    "Context",
    "ContextBlock",
    "ContextBuilderConfig",
    "ContextBuilderPipeline",
    "ContextBuilderRegistry",
    "ContextMetadata",
    "IConflictDetector",
    "IContextCompressor",
    "IContextStitcher",
    "ITokenBudgetAllocator",
]
