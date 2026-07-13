"""Passthrough strategy for integration tests."""

from __future__ import annotations

from core.chunking.builder import _base_metadata, _render_element
from core.chunking.interfaces import ChunkingStrategy
from core.chunking.models import (
    BoundaryDecision,
    Chunk,
    ChunkIdentity,
    ChunkLineage,
    ChunkingStrategyConfig,
    ChunkSet,
    StructuralContext,
    ValidationReport,
    compute_config_hash,
)
from core.chunking.validator import ChunkValidator
from core.document_intelligence.model import DocumentModel
import hashlib


class PassthroughChunkingStrategy(ChunkingStrategy):
    """Emit one chunk per structural element without merging."""

    def __init__(self, config: ChunkingStrategyConfig | None = None) -> None:
        self._config = config or ChunkingStrategyConfig()

    @property
    def strategy_id(self) -> str:
        return "passthrough"

    def chunk(self, document_model: DocumentModel, config: ChunkingStrategyConfig) -> ChunkSet:
        chunks: list[Chunk] = []
        config_hash = compute_config_hash(config)
        asset_id = str(document_model.asset_id)
        for position, element in enumerate(document_model.elements):
            text = _render_element(element)
            sorted_ids = [element.id]
            payload = f"{asset_id}|{element.id}|{self.strategy_id}|{config_hash}"
            chunk_id = f"ck_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"
            lineage = ChunkLineage(
                source_element_ids=[element.id],
                applied_rule="passthrough",
                triggered_features=["size_budget"],
                rationale="One element per chunk",
            )
            metadata = _base_metadata([element], text, file_name=None)
            metadata.update(
                {
                    "chunk_id": chunk_id,
                    "parent_chunk_id": None,
                    "previous_chunk_id": None,
                    "next_chunk_id": None,
                    "heading_path": [],
                    "chunk_position": position,
                    "lineage": lineage.model_dump(),
                    "child_chunk_ids": [],
                }
            )
            chunks.append(
                Chunk(
                    text=text,
                    metadata=metadata,
                    identity=ChunkIdentity(
                        chunk_id=chunk_id,
                        document_id=asset_id,
                        strategy_id=self.strategy_id,
                        source_element_ids=sorted_ids,
                    ),
                    lineage=lineage,
                    structural_context=StructuralContext(
                        element_type=element.type,
                        heading_path=[],
                        position=position,
                    ),
                )
            )
        validator = ChunkValidator(config)
        report = validator.validate(chunks)
        return ChunkSet(
            chunks=chunks,
            validation_report=report,
            asset_id=asset_id,
            strategy_id=self.strategy_id,
            element_counts_by_type=document_model.element_counts(),
        )
