"""RecommendationTrace for operator diagnostics (018-aligned; not a public API)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from services.rag.recommend.models import RecommendationCandidate, RecommendationDecision


class RecommendationTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str | None = None
    need_frame_summary: dict[str, Any] = Field(default_factory=dict)
    taxonomy_mapping: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    candidates: list[RecommendationCandidate] = Field(default_factory=list)
    decision: RecommendationDecision | None = None

    def to_diagnostics(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "need_frame_summary": self.need_frame_summary,
            "taxonomy_mapping": self.taxonomy_mapping,
            "constraints": self.constraints,
            "candidate_count": len(self.candidates),
            "decision_type": (
                self.decision.decision_type if self.decision is not None else None
            ),
            "candidates": [
                {
                    "candidate_id": c.candidate_id,
                    "brand": c.product_identity.brand,
                    "line": c.product_identity.product_line,
                    "matched_indications": c.matched_indications,
                    "safety_outcome": c.safety_outcome,
                    "rank_contribution": c.signal_breakdown,
                    "score": c.recommendation_score,
                    "retained": c.retained,
                }
                for c in self.candidates
            ],
        }


def build_trace(
    *,
    correlation_id: str | None,
    need_frame_summary: dict[str, Any],
    taxonomy_mapping: dict[str, Any],
    constraints: dict[str, Any],
    candidates: list[RecommendationCandidate],
    decision: RecommendationDecision,
) -> RecommendationTrace:
    return RecommendationTrace(
        correlation_id=correlation_id,
        need_frame_summary=need_frame_summary,
        taxonomy_mapping=taxonomy_mapping,
        constraints=constraints,
        candidates=candidates,
        decision=decision,
    )
