"""Recommend-mode models (internal sole-path helpers — not a production owner)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

IdentityLevel = Literal["brand", "line", "strength", "package"]
SafetyOutcomeKind = Literal["pass", "demote", "exclude", "unknown"]
DecisionType = Literal["recommend", "clarify", "refuse", "limited_coverage"]


class ProductIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str
    product_line: str | None = None
    strength: str | None = None
    package: str | None = None
    inn: str | None = None
    identity_level: IdentityLevel = "line"


class SafetyLabel(BaseModel):
    """Extensible dimension map; missing keys ⇒ unknown."""

    model_config = ConfigDict(extra="allow")

    pregnancy: str | None = None
    breastfeeding: str | None = None
    pediatric: str | None = None
    elderly: str | None = None
    renal_impairment: str | None = None
    hepatic_impairment: str | None = None
    diabetes: str | None = None
    hypertension: str | None = None
    contraindications: str | None = None
    interaction_severity: str | None = None
    otc_prescription: str | None = None


class RankingSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indication_match: float | None = None
    retrieval_evidence: float | None = None
    reranker_confidence: float | None = None
    safety_fitness: float | None = None
    formulary_preference: float | None = None


class RecommendationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    product_identity: ProductIdentity
    matched_indications: list[str] = Field(default_factory=list)
    evidence_pointers: list[str] = Field(default_factory=list)
    safety_outcome: SafetyOutcomeKind = "unknown"
    safety_dimensions: dict[str, str] = Field(default_factory=dict)
    ranking_signals: RankingSignals = Field(default_factory=RankingSignals)
    recommendation_score: float = 0.0
    signal_breakdown: dict[str, float] = Field(default_factory=dict)
    retained: bool = False
    in_corpus: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_type: DecisionType
    ordered_candidates: list[RecommendationCandidate] = Field(default_factory=list)
    clarification_prompt: str | None = None
    policy_bounds_applied: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"
    message: str | None = None
