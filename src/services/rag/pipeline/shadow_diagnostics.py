"""Shadow dual-run diagnostic helpers."""

from __future__ import annotations

import difflib
from typing import Iterable

from services.rag.pipeline.models import PipelineOutcome, ShadowComparisonRecord


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = {x for x in a if x}
    set_b = {x for x in b if x}
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def answer_similarity(a: str | None, b: str | None) -> float:
    left = (a or "").strip().lower()
    right = (b or "").strip().lower()
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def retrieval_overlap(legacy_ids: Iterable[str], unified_ids: Iterable[str]) -> float:
    return jaccard_similarity(legacy_ids, unified_ids)


def evidence_overlap(legacy_ids: Iterable[str], evidence_doc_ids: Iterable[str]) -> float:
    return jaccard_similarity(legacy_ids, evidence_doc_ids)


def plan_strategy_match(legacy_path: str | None, unified_strategies: Iterable[str] | None) -> bool | None:
    if legacy_path is None or unified_strategies is None:
        return None
    strategies = {s.lower() for s in unified_strategies}
    path = (legacy_path or "").lower()
    if "interaction" in path:
        return "structured_interaction" in strategies or "structured" in strategies
    if "entity" in path or "vector" in path:
        return bool(strategies & {"dense", "semantic", "sparse", "keyword", "mixed"})
    return bool(strategies)


def first_divergent_stage(
    *,
    legacy_outcome: PipelineOutcome,
    unified_outcome: PipelineOutcome,
    retrieval_overlap_score: float | None,
    evidence_overlap_score: float | None,
    answer_sim: float | None,
    divergence_threshold: float,
    legacy_stage_statuses: dict[str, str] | None = None,
    unified_stage_statuses: dict[str, str] | None = None,
) -> str | None:
    if legacy_outcome != unified_outcome:
        if legacy_stage_statuses and unified_stage_statuses:
            for stage in ("parse", "plan", "retrieve", "evidence", "context", "answer"):
                if legacy_stage_statuses.get(stage) != unified_stage_statuses.get(stage):
                    return stage
        return "answer"
    if retrieval_overlap_score is not None and retrieval_overlap_score < 0.5:
        return "retrieve"
    if evidence_overlap_score is not None and evidence_overlap_score < 0.5:
        return "evidence"
    if answer_sim is not None and answer_sim < divergence_threshold:
        return "answer"
    return None


def build_shadow_record(**kwargs) -> ShadowComparisonRecord:
    return ShadowComparisonRecord(**kwargs)
