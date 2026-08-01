"""Recommendation decision assembly (recommend / clarify / refuse / limited)."""

from __future__ import annotations

from typing import Any

from core.query_parser.need_frame import NeedFrame
from services.rag.recommend.identity import collapse_package_variants, prefer_need_specific_line
from services.rag.recommend.pack_access import load_recommendation_policy
from services.rag.recommend.models import RecommendationCandidate, RecommendationDecision
from services.rag.recommend.policy import (
    apply_count_bounds,
    clarification_threshold,
    filter_out_of_corpus,
)
from services.rag.recommend.ranking import apply_ranking
from services.rag.recommend.safety import apply_safety_filter
from services.rag.recommend.trace import RecommendationTrace, build_trace


def decide(
    *,
    need_frame: NeedFrame | None,
    candidates: list[RecommendationCandidate],
    language: str = "en",
    corpus_ids: set[str] | None = None,
    policy: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    taxonomy_mapping: dict[str, Any] | None = None,
) -> tuple[RecommendationDecision, RecommendationTrace]:
    pol = policy or load_recommendation_policy()
    nf = need_frame or NeedFrame()
    lang = (language or nf.language or "en")[:2]

    conf = float(nf.confidence or 0.0)
    threshold = clarification_threshold(pol)

    if nf.ambiguity_group or (
        pol.get("clarify_instead_of_guessing", True) and conf < threshold
    ):
        prompt = None
        if taxonomy_mapping:
            prompt = taxonomy_mapping.get("clarification_prompt")
        if not prompt:
            prompt = (
                "هل يمكنك توضيح العرض أو الحاجة العلاجية بشكل أدق؟"
                if lang == "ar"
                else "Could you clarify the symptom or therapeutic need more precisely?"
            )
        decision = RecommendationDecision(
            decision_type="clarify",
            ordered_candidates=[],
            clarification_prompt=str(prompt),
            language=lang,
            policy_bounds_applied={"clarification_confidence_threshold": threshold},
        )
        trace = build_trace(
            correlation_id=correlation_id,
            need_frame_summary=nf.model_dump(),
            taxonomy_mapping=taxonomy_mapping or {},
            constraints={"reason": "low_confidence_or_ambiguity"},
            candidates=candidates,
            decision=decision,
        )
        return decision, trace

    corpus_filtered = filter_out_of_corpus(candidates, corpus_ids=corpus_ids, policy=pol)
    if not corpus_filtered:
        decision = RecommendationDecision(
            decision_type="limited_coverage",
            ordered_candidates=[],
            language=lang,
            message=(
                "لا تتوفر توصيات كافية ضمن فهرس المشروع الحالي."
                if lang == "ar"
                else "Insufficient in-corpus options for a recommendation."
            ),
        )
        trace = build_trace(
            correlation_id=correlation_id,
            need_frame_summary=nf.model_dump(),
            taxonomy_mapping=taxonomy_mapping or {},
            constraints={"corpus_empty": True},
            candidates=candidates,
            decision=decision,
        )
        return decision, trace

    safety_applied = apply_safety_filter(
        corpus_filtered, population=nf.population
    )
    usable = [c for c in safety_applied if c.safety_outcome != "exclude"]
    if not usable:
        decision = RecommendationDecision(
            decision_type="refuse",
            ordered_candidates=safety_applied,
            language=lang,
            message=(
                "لا يمكن تقديم توصية أولى آمنة لهذه الفئة؛ يُرجى استشارة صيدلي/طبيب."
                if lang == "ar"
                else "No safe first-line recommendation for this population; consult a pharmacist/physician."
            ),
        )
        trace = build_trace(
            correlation_id=correlation_id,
            need_frame_summary=nf.model_dump(),
            taxonomy_mapping=taxonomy_mapping or {},
            constraints={"all_excluded_by_safety": True},
            candidates=safety_applied,
            decision=decision,
        )
        return decision, trace

    ranked = apply_ranking(usable, policy=pol)
    ranked = prefer_need_specific_line(ranked, need_tags=list(nf.indication_tags or []))
    ranked = collapse_package_variants(ranked, policy=pol)
    bounded, bounds_meta = apply_count_bounds(ranked, policy=pol)

    decision = RecommendationDecision(
        decision_type="recommend",
        ordered_candidates=bounded,
        language=lang,
        policy_bounds_applied=bounds_meta,
    )
    trace = build_trace(
        correlation_id=correlation_id,
        need_frame_summary=nf.model_dump(),
        taxonomy_mapping=taxonomy_mapping or {},
        constraints={"population": nf.population},
        candidates=safety_applied,
        decision=decision,
    )
    return decision, trace
