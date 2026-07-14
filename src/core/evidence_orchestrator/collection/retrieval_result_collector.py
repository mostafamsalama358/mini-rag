"""Collect stage — map RetrievalResult candidates to CollectedItem objects."""

from __future__ import annotations

import logging
import time

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import IEvidenceCollector, ITokenCounter
from core.evidence_orchestrator.models import CollectedItem, EvidenceItemSource
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from core.evidence_orchestrator.token_counting.tiktoken_counter import (
    TiktokenTokenCounter,
)
from core.retrieval_engine.models import RetrievalResult
from core.retrieval_planner.models import RetrievalPlan

logger = logging.getLogger(__name__)


class RetrievalResultCollector(IEvidenceCollector):
    def __init__(self, token_counter: ITokenCounter | None = None) -> None:
        self._token_counter = token_counter or CharacterApproximationTokenCounter()

    async def collect(
        self,
        result: RetrievalResult,
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]:
        started = time.perf_counter()
        counter = self._resolve_token_counter(config)
        collected: list[CollectedItem] = []

        for index, candidate in enumerate(result.candidates):
            strategy_id = _resolve_strategy_id(result, index)
            text = candidate.content_excerpt or ""
            source = EvidenceItemSource(
                strategy_id=strategy_id,
                raw_score=float(candidate.score),
            )
            collected.append(
                CollectedItem(
                    candidate=candidate,
                    strategy_id=strategy_id,
                    raw_token_count=counter.count_tokens(text),
                    contributing_sources=[source],
                )
            )

        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "stage=collect plan_id=%s input_count=%d output_count=%d latency_ms=%.2f",
            plan.metadata.plan_id,
            len(result.candidates),
            len(collected),
            latency_ms,
        )
        return collected

    def _resolve_token_counter(
        self, config: EvidenceOrchestratorConfig
    ) -> ITokenCounter:
        if config.token_counter == "tiktoken":
            try:
                return TiktokenTokenCounter()
            except ImportError:
                logger.warning(
                    "tiktoken unavailable; falling back to character approximation"
                )
        return self._token_counter


def _resolve_strategy_id(result: RetrievalResult, index: int) -> str:
    steps = [s for s in result.trace.steps if not s.skipped and s.strategy]
    if index < len(steps):
        return steps[index].strategy
    strategies = list(result.metadata.executed_strategies)
    if strategies:
        return strategies[index % len(strategies)]
    return "unknown"
