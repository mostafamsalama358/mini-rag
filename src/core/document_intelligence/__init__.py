"""Generic Document Intelligence: parse → DocumentModel → structure-aware chunks."""

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.model import (
    CANONICAL_ELEMENT_TYPES,
    DocumentModel,
    StructuralElement,
    StructuralElementType,
)
from core.document_intelligence.chunk_mapper import map_elements_to_chunks
from core.document_intelligence.fallback import build_fallback_model

__all__ = [
    "CANONICAL_ELEMENT_TYPES",
    "DocumentIntelligenceDegraded",
    "DocumentModel",
    "StructuralElement",
    "StructuralElementType",
    "build_fallback_model",
    "map_elements_to_chunks",
]
