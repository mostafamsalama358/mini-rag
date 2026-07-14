"""Relationship candidate validation helper (research R5 sub-stage 2)."""

from __future__ import annotations

import logging

from core.knowledge.models import (
    KnowledgeRelationship,
    KnowledgeRelationshipMetadata,
    KnowledgeUnit,
    RelationshipCandidate,
    utc_now_iso,
)

logger = logging.getLogger(__name__)


class RelationshipCandidateValidator:
    """Filter dangling/self/cycle candidates into KnowledgeRelationships."""

    def __init__(self, *, discoverer_strategy_id: str = "structural") -> None:
        self.discoverer_strategy_id = discoverer_strategy_id
        self.dropped_dangling_count = 0

    def validate(
        self,
        candidates: list[RelationshipCandidate],
        units: list[KnowledgeUnit],
    ) -> list[KnowledgeRelationship]:
        unit_ids = {u.id for u in units}
        accepted: list[KnowledgeRelationship] = []
        sequence_edges: set[tuple[str, str]] = set()
        self.dropped_dangling_count = 0

        for candidate in candidates:
            if (
                candidate.source_unit_id not in unit_ids
                or candidate.target_unit_id not in unit_ids
            ):
                self.dropped_dangling_count += 1
                logger.info(
                    "dropped dangling relationship candidate source=%s target=%s",
                    candidate.source_unit_id,
                    candidate.target_unit_id,
                )
                continue
            if candidate.source_unit_id == candidate.target_unit_id:
                continue
            if candidate.relationship_type == "sequence":
                edge = (candidate.source_unit_id, candidate.target_unit_id)
                reverse = (candidate.target_unit_id, candidate.source_unit_id)
                if reverse in sequence_edges:
                    continue
                sequence_edges.add(edge)

            accepted.append(
                KnowledgeRelationship(
                    relationship_type=candidate.relationship_type,
                    source_unit_id=candidate.source_unit_id,
                    target_unit_id=candidate.target_unit_id,
                    evidence_references=candidate.evidence_references,
                    attributes={"directed": True, "rationale": candidate.rationale},
                    metadata=KnowledgeRelationshipMetadata(
                        discoverer_strategy_id=self.discoverer_strategy_id,
                        created_at=utc_now_iso(),
                    ),
                )
            )
        return accepted
