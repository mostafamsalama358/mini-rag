"""Prioritize stage — weighted relevance fusion ranking."""

from __future__ import annotations

import logging
import time

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import IEvidencePrioritizer
from core.evidence_orchestrator.models import EvidenceItem
from core.evidence_orchestrator.text_similarity import clamp
from core.retrieval_planner.models import RetrievalPlan

logger = logging.getLogger(__name__)


class FusionPrioritizer(IEvidencePrioritizer):
    async def prioritize(
        self,
        items: list[EvidenceItem],
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> list[EvidenceItem]:
        started = time.perf_counter()
        if not items:
            return []

        retrieval_scores = [item.citation.retrieval_score for item in items]
        norm_scores = _min_max_normalize(retrieval_scores)
        recency_scores = _recency_scores(items)
        entity_count = max(1, len(plan.entities))
        weights = config.fusion_weights

        prioritized: list[EvidenceItem] = []
        entity_matches_total = 0
        recency_signals = 0

        for item, norm_ret, recency in zip(
            items, norm_scores, recency_scores, strict=True
        ):
            matched = _match_entities(item.text, plan)
            entity_matches_total += len(matched)
            entity_ratio = min(1.0, len(matched) / entity_count)
            if recency != 0.5:
                recency_signals += 1

            final_score = clamp(
                weights.retrieval * norm_ret
                + weights.entity * entity_ratio
                + weights.recency * recency
            )
            prioritized.append(
                item.model_copy(
                    update={
                        "relevance_score": final_score,
                        "entity_tags": matched,
                    }
                )
            )

        prioritized.sort(key=lambda i: i.relevance_score, reverse=True)
        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "stage=prioritize input_count=%d output_count=%d "
            "entity_matches_total=%d recency_signals_present=%d latency_ms=%.2f",
            len(items),
            len(prioritized),
            entity_matches_total,
            recency_signals,
            latency_ms,
        )
        return prioritized


def _min_max_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if lo == hi:
        return [1.0 for _ in values]
    span = hi - lo
    return [(v - lo) / span for v in values]


def _recency_scores(items: list[EvidenceItem]) -> list[float]:
    indices = [
        item.citation.chunk_index
        for item in items
        if item.citation.chunk_index is not None
    ]
    if not indices:
        return [0.5 for _ in items]

    lo = min(indices)
    hi = max(indices)
    if lo == hi:
        return [1.0 if item.citation.chunk_index is not None else 0.5 for item in items]

    scores: list[float] = []
    for item in items:
        idx = item.citation.chunk_index
        if idx is None:
            scores.append(0.5)
        else:
            scores.append((idx - lo) / (hi - lo))
    return scores


def _match_entities(text: str, plan: RetrievalPlan) -> list[str]:
    haystack = text.lower()
    matched: list[str] = []
    for entity in plan.entities:
        needle = entity.canonical_form.lower()
        if needle and needle in haystack:
            matched.append(entity.canonical_form)
    return matched
