"""Default structural KnowledgeUnitExtractor (research R3 / R8 / R9)."""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from core.chunking.models import Chunk, ChunkSet
from core.knowledge.errors import EvidenceIntegrityError
from core.knowledge.interfaces import KnowledgeUnitExtractor
from core.knowledge.models import (
    EvidenceReference,
    KnowledgeExtractionConfig,
    KnowledgeUnit,
    KnowledgeUnitMetadata,
    KnowledgeUnitType,
    compute_config_hash,
    make_evidence_reference_id,
    utc_now_iso,
)

logger = logging.getLogger(__name__)

_PROC_RE = re.compile(r"(?m)^\s*(?:\d+\.|Step\s+\d+)", re.IGNORECASE)
_DEF_RE = re.compile(r"\b(is defined as|means|refers to|is the)\b", re.IGNORECASE)
_MEAS_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mg|g|kg|ml|mL|µg|mcg|%|mmHg|mmol|IU)\b"
)
_LIST_SPLIT_RE = re.compile(r"(?m)^\s*[-*•]\s+|^\s*\d+\.\s+")
_DEF_SPLIT_RE = re.compile(
    r"\b(?:is defined as|means|refers to|is the)\b", re.IGNORECASE
)


def build_evidence_reference(chunk: Chunk, chunk_set: ChunkSet) -> EvidenceReference:
    """Construct a four-level EvidenceReference from a Chunk (T021)."""
    if chunk.identity is None:
        raise EvidenceIntegrityError("Chunk.identity is required for evidence")
    chunk_ids = [chunk.identity.chunk_id]
    element_ids = list(chunk.identity.source_element_ids)
    document_model_id = chunk.identity.document_id
    asset_id = chunk_set.asset_id
    if not chunk_ids or not chunk_ids[0]:
        raise EvidenceIntegrityError("chunk_ids must be non-empty")
    if not element_ids:
        raise EvidenceIntegrityError("element_ids must be non-empty")
    if not document_model_id:
        raise EvidenceIntegrityError("document_model_id must be non-empty")
    if not asset_id:
        raise EvidenceIntegrityError("asset_id must be non-empty")
    return EvidenceReference(
        id=make_evidence_reference_id(
            chunk_ids=chunk_ids,
            element_ids=element_ids,
            document_model_id=document_model_id,
            asset_id=asset_id,
        ),
        chunk_ids=chunk_ids,
        element_ids=element_ids,
        document_model_id=document_model_id,
        asset_id=asset_id,
    )


def _classify(chunk: Chunk) -> KnowledgeUnitType:
    text = chunk.text or ""
    element_type = (
        chunk.structural_context.element_type if chunk.structural_context else ""
    )
    if _PROC_RE.search(text):
        return "procedure"
    if _DEF_RE.search(text):
        return "definition"
    if _MEAS_RE.search(text):
        return "measurement"
    if element_type in {"table", "table-row"}:
        return "table"
    if element_type in {"list", "list-item"}:
        return "list"
    if element_type in {"code-block", "quote", "figure-placeholder"}:
        return "structured_observation"
    if element_type == "heading":
        return "assertion"
    return "fact"


def _semantic_content(unit_type: KnowledgeUnitType, chunk: Chunk) -> dict[str, Any]:
    text = chunk.text or ""
    element_type = (
        chunk.structural_context.element_type if chunk.structural_context else ""
    )
    if unit_type == "definition":
        parts = _DEF_SPLIT_RE.split(text, maxsplit=1)
        if len(parts) == 2:
            return {"term": parts[0].strip(), "definition": parts[1].strip()}
        return {"text": text}
    if unit_type == "measurement":
        match = _MEAS_RE.search(text)
        if match:
            return {
                "value": match.group(1),
                "unit": match.group(2),
                "context": text,
            }
        return {"text": text}
    if unit_type == "procedure":
        steps = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and _PROC_RE.match(line)
        ]
        if steps:
            return {"steps": steps}
        return {"text": text}
    if unit_type == "list":
        items = [p.strip() for p in _LIST_SPLIT_RE.split(text) if p.strip()]
        if len(items) > 1:
            return {"items": items}
        return {"text": text}
    if unit_type == "table":
        rows_meta = (chunk.metadata or {}).get("rows")
        if isinstance(rows_meta, list):
            return {"rows": rows_meta}
        return {"text": text}
    if unit_type == "structured_observation":
        return {"text": text, "element_type": element_type}
    return {"text": text}


def _participants(
    unit_type: KnowledgeUnitType, semantic_content: dict[str, Any]
) -> dict[str, Any] | None:
    if unit_type == "definition" and "term" in semantic_content:
        return {"subject": semantic_content["term"]}
    if unit_type == "procedure":
        return {"agent": None}
    return None


class StructuralKnowledgeUnitExtractor(KnowledgeUnitExtractor):
    """Deterministic structure/regex-based extractor (default strategy)."""

    @property
    def strategy_id(self) -> str:
        return "structural"

    def extract(
        self,
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]:
        config_hash = compute_config_hash(config)
        units: list[KnowledgeUnit] = []
        for chunk in chunk_set.chunks:
            unit_type = _classify(chunk)
            evidence = build_evidence_reference(chunk, chunk_set)
            semantic = _semantic_content(unit_type, chunk)
            units.append(
                KnowledgeUnit(
                    type=unit_type,
                    semantic_content=semantic,
                    participants=_participants(unit_type, semantic),
                    attributes={"source_surface_form": chunk.text or ""},
                    evidence_references=(evidence,),
                    relationships=(),
                    metadata=KnowledgeUnitMetadata(
                        extractor_strategy_id=self.strategy_id,
                        normalization_status="raw",
                        created_at=utc_now_iso(),
                        config_hash=config_hash,
                    ),
                )
            )

        counts = Counter(u.type for u in units)
        logger.info(
            "knowledge_extraction asset_id=%s chunk_count=%s ku_count_by_type=%s "
            "extractor_strategy_id=%s",
            chunk_set.asset_id,
            len(chunk_set.chunks),
            dict(counts),
            self.strategy_id,
        )
        return units
