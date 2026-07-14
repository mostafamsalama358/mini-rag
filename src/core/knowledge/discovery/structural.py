"""Structural RelationshipDiscoverer (research R5)."""

from __future__ import annotations

import logging

from core.chunking.models import ChunkSet
from core.knowledge.discovery.validator import RelationshipCandidateValidator
from core.knowledge.interfaces import RelationshipDiscoverer
from core.knowledge.models import (
    EvidenceReference,
    KnowledgeExtractionConfig,
    KnowledgeRelationship,
    KnowledgeUnit,
    RelationshipCandidate,
)

logger = logging.getLogger(__name__)


def _union_evidence(*units: KnowledgeUnit) -> tuple[EvidenceReference, ...]:
    seen: dict[str, EvidenceReference] = {}
    for unit in units:
        for ref in unit.evidence_references:
            seen[ref.id] = ref
    return tuple(seen.values())


class StructuralRelationshipDiscoverer(RelationshipDiscoverer):
    """Produce sequence, containment, and elaboration candidates from structure."""

    def __init__(self) -> None:
        self._validator = RelationshipCandidateValidator(
            discoverer_strategy_id=self.strategy_id
        )

    @property
    def strategy_id(self) -> str:
        return "structural"

    def generate_candidates(
        self,
        units: list[KnowledgeUnit],
        chunk_set: ChunkSet,
        config: KnowledgeExtractionConfig,
    ) -> list[RelationshipCandidate]:
        candidates: list[RelationshipCandidate] = []

        # (a) sequence for adjacent KUs
        for i in range(len(units) - 1):
            left, right = units[i], units[i + 1]
            candidates.append(
                RelationshipCandidate(
                    source_unit_id=left.id,
                    target_unit_id=right.id,
                    relationship_type="sequence",
                    evidence_references=_union_evidence(left, right),
                    rationale="adjacent units in normalized reading order",
                    score=None,
                )
            )

        # Map chunk_id -> unit for containment / heading lookups
        chunk_to_unit: dict[str, KnowledgeUnit] = {}
        for unit in units:
            for ref in unit.evidence_references:
                for chunk_id in ref.chunk_ids:
                    chunk_to_unit.setdefault(chunk_id, unit)

        # (b) containment from parent_chunk_id
        for chunk in chunk_set.chunks:
            if chunk.identity is None:
                continue
            parent_id = chunk.relationships.parent_chunk_id
            if not parent_id:
                continue
            child_unit = chunk_to_unit.get(chunk.identity.chunk_id)
            parent_unit = chunk_to_unit.get(parent_id)
            if child_unit is None or parent_unit is None:
                continue
            if child_unit.id == parent_unit.id:
                continue
            candidates.append(
                RelationshipCandidate(
                    source_unit_id=parent_unit.id,
                    target_unit_id=child_unit.id,
                    relationship_type="containment",
                    evidence_references=parent_unit.evidence_references,
                    rationale="parent/child chunk relationship",
                    score=None,
                )
            )

        # (c) elaboration for shared heading_path prefix
        heading_groups: dict[tuple[str, ...], list[KnowledgeUnit]] = {}
        for chunk in chunk_set.chunks:
            if chunk.identity is None or chunk.structural_context is None:
                continue
            unit = chunk_to_unit.get(chunk.identity.chunk_id)
            if unit is None:
                continue
            path = tuple(chunk.structural_context.heading_path)
            if not path:
                continue
            heading_groups.setdefault(path, []).append(unit)

        for path, group in heading_groups.items():
            # de-dupe while preserving order
            seen: set[str] = set()
            ordered: list[KnowledgeUnit] = []
            for unit in group:
                if unit.id in seen:
                    continue
                seen.add(unit.id)
                ordered.append(unit)
            if len(ordered) < 2:
                continue
            head = ordered[0]
            for other in ordered[1:]:
                candidates.append(
                    RelationshipCandidate(
                        source_unit_id=head.id,
                        target_unit_id=other.id,
                        relationship_type="elaboration",
                        evidence_references=_union_evidence(head, other),
                        rationale=f"shared heading_path {list(path)}",
                        score=None,
                    )
                )

        return candidates

    def validate_candidates(
        self,
        candidates: list[RelationshipCandidate],
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeRelationship]:
        relationships = self._validator.validate(candidates, units)
        logger.info(
            "knowledge_discovery candidate_count=%s validated_relationship_count=%s "
            "dropped_dangling_count=%s discoverer_strategy_id=%s",
            len(candidates),
            len(relationships),
            self._validator.dropped_dangling_count,
            self.strategy_id,
        )
        return relationships
