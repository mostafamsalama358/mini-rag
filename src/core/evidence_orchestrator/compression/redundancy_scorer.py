"""Compress-flag stage — advisory compressibility scoring."""

from __future__ import annotations

import logging
import time

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import ICompressibilityScorer
from core.evidence_orchestrator.models import EvidenceItem
from core.evidence_orchestrator.text_similarity import char_ngrams, clamp

logger = logging.getLogger(__name__)


class RedundancyScorer(ICompressibilityScorer):
    async def score(
        self,
        items: list[EvidenceItem],
        config: EvidenceOrchestratorConfig,
    ) -> list[EvidenceItem]:
        started = time.perf_counter()
        if not items:
            return []

        ordered = sorted(items, key=lambda i: i.relevance_score, reverse=True)
        union_above: set[str] = set()
        scored: list[EvidenceItem] = []
        high_compressibility = 0
        weights = config.compressibility_weights

        for item in ordered:
            try:
                if not (item.text or "").strip():
                    raise ValueError("empty text")
                ngrams_i = char_ngrams(item.text)
                if union_above:
                    union_ngrams = union_above
                    redundancy = len(ngrams_i & union_ngrams) / max(
                        1, len(ngrams_i | union_ngrams)
                    )
                else:
                    redundancy = 0.0

                relevance_inverse = 1.0 - item.relevance_score
                score = clamp(
                    weights.redundancy * redundancy
                    + weights.relevance_inverse * relevance_inverse
                )
                if score > 0.7:
                    high_compressibility += 1
                scored.append(
                    item.model_copy(update={"compressibility_score": score})
                )
                union_above |= ngrams_i
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "compressibility_item_failed item_id=%s error=%s",
                    item.item_id,
                    exc,
                )
                scored.append(item.model_copy(update={"compressibility_score": 0.5}))

        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "stage=compress_flag input_count=%d output_count=%d "
            "high_compressibility_count=%d latency_ms=%.2f",
            len(items),
            len(scored),
            high_compressibility,
            latency_ms,
        )
        return scored
