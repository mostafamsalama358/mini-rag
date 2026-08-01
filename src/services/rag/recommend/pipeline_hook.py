"""Sole-path recommend hook invoked from UnifiedRagOrchestrator (Feature 020)."""

from __future__ import annotations

import logging
from typing import Any

from core.query_parser.need_frame import NeedFrame
from services.rag.recommend.constraints import (
    merge_retrieval_evidence,
    metadata_filter_for_tags,
    seed_candidates_for_tags,
)
from services.rag.recommend.decision import decide
from services.rag.recommend.models import RecommendationDecision
from services.rag.recommend.trace import RecommendationTrace

logger = logging.getLogger("uvicorn.error")


def is_recommend_plan(query_plan: Any) -> bool:
    if query_plan is None:
        return False
    if bool(getattr(query_plan, "recommend_mode", False)):
        return True
    return getattr(query_plan, "operation", None) == "recommend"


def enrich_retrieval_metadata_for_recommend(
    metadata: dict[str, Any],
    query_plan: Any,
) -> dict[str, Any]:
    if not is_recommend_plan(query_plan):
        return metadata
    nf: NeedFrame | None = getattr(query_plan, "need_frame", None)
    tags = list(getattr(nf, "indication_tags", None) or [])
    if not tags:
        tags = list((getattr(query_plan, "filters", None) or {}).get("indication_tags") or [])
    extra = metadata_filter_for_tags(tags)
    out = dict(metadata)
    out["recommend_mode"] = True
    # Avoid hard entity scope for open recommend
    out.pop("entity_prefix", None)
    out["entity_prefixes"] = []
    mf = dict(out.get("metadata_filter") or {})
    mf.update(extra)
    out["metadata_filter"] = mf
    out["indication_tags"] = tags
    return out


def run_recommend_decision(
    *,
    query_plan: Any,
    retrieval_candidates: list[Any] | None = None,
    correlation_id: str | None = None,
) -> tuple[RecommendationDecision | None, RecommendationTrace | None]:
    if not is_recommend_plan(query_plan):
        return None, None
    nf: NeedFrame | None = getattr(query_plan, "need_frame", None)
    tags = list(getattr(nf, "indication_tags", None) or [])
    seeded = seed_candidates_for_tags(tags)

    evidence_by_brand: dict[str, float] = {}
    for doc in retrieval_candidates or []:
        meta = getattr(doc, "metadata", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        brand = str(
            meta.get("brand_name")
            or meta.get("col_med")
            or meta.get("entity")
            or ""
        ).strip()
        if not brand:
            continue
        score = float(getattr(doc, "score", 0.0) or 0.0)
        key = brand.casefold()
        evidence_by_brand[key] = max(evidence_by_brand.get(key, 0.0), score)

    merged = merge_retrieval_evidence(seeded, evidence_by_brand=evidence_by_brand)
    taxonomy_mapping = {
        "indication_tags": tags,
        "clarification_prompt": getattr(query_plan, "clarification_prompt", None),
        "node_ids": list(getattr(nf, "taxonomy_node_ids", None) or []) if nf else [],
    }
    decision, trace = decide(
        need_frame=nf,
        candidates=merged,
        language=getattr(query_plan, "language", "en") or "en",
        corpus_ids=None,
        correlation_id=correlation_id,
        taxonomy_mapping=taxonomy_mapping,
    )
    return decision, trace
