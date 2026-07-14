"""Evidence Orchestrator pipeline — six-stage async orchestration."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.errors import (
    CollectionError,
    CompressibilityScoringError,
    DeduplicationError,
    ExpansionError,
    PackagingError,
    PrioritizationError,
)
from core.evidence_orchestrator.interfaces import (
    IChunkReader,
    ICompressibilityScorer,
    IDeduplicator,
    IEvidenceCollector,
    IEvidenceExpander,
    IEvidencePrioritizer,
    ITokenCounter,
)
from core.evidence_orchestrator.models import (
    EvidencePack,
    OrchestratorStageTrace,
    OrchestratorTrace,
    SCHEMA_VERSION,
)
from core.evidence_orchestrator.packaging.pack_assembler import PackAssembler
from core.retrieval_engine.models import RetrievalResult
from core.retrieval_planner.models import RetrievalPlan

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EvidenceOrchestrator:
    def __init__(
        self,
        *,
        collector: IEvidenceCollector,
        deduplicator: IDeduplicator,
        expander: IEvidenceExpander,
        compressibility_scorer: ICompressibilityScorer,
        prioritizer: IEvidencePrioritizer,
        pack_assembler: PackAssembler,
        chunk_reader: IChunkReader,
        token_counter: ITokenCounter,
    ) -> None:
        self._collector = collector
        self._deduplicator = deduplicator
        self._expander = expander
        self._compressibility_scorer = compressibility_scorer
        self._prioritizer = prioritizer
        self._pack_assembler = pack_assembler
        self._chunk_reader = chunk_reader
        self._token_counter = token_counter

    async def orchestrate(
        self,
        result: RetrievalResult,
        plan: RetrievalPlan,
        config: EvidenceOrchestratorConfig,
    ) -> EvidencePack:
        started = time.perf_counter()
        stage_traces: list[OrchestratorStageTrace] = []
        dedup_method = "exact_only"
        created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        if not result.candidates:
            trace = OrchestratorTrace(
                stages=[],
                total_latency_ms=(time.perf_counter() - started) * 1000.0,
                dedup_method_used="exact_only",
                expansion_enabled=config.expansion_enabled,
            )
            return self._pack_assembler.assemble(
                items=[],
                result=result,
                plan=plan,
                trace=trace,
                raw_input_token_count=0,
                created_at=created_at,
            )

        raw_input_token_count = sum(
            self._token_counter.count_tokens(c.content_excerpt or "")
            for c in result.candidates
        )

        collected = await _run_stage(
            "collect",
            len(result.candidates),
            lambda: self._collector.collect(result, plan, config),
            stage_traces,
            CollectionError,
        )

        deduped = await _run_stage(
            "deduplicate",
            len(collected),
            lambda: self._deduplicator.deduplicate(collected, config),
            stage_traces,
            DeduplicationError,
        )
        if hasattr(self._deduplicator, "last_method_used"):
            dedup_method = self._deduplicator.last_method_used  # type: ignore[attr-defined]

        expanded = await _run_stage(
            "expand",
            len(deduped),
            lambda: self._expander.expand(deduped, self._chunk_reader, config),
            stage_traces,
            ExpansionError,
        )

        evidence_items = self._pack_assembler.collected_to_evidence_items(expanded)

        scored = await _run_stage(
            "compress_flag",
            len(evidence_items),
            lambda: self._compressibility_scorer.score(evidence_items, config),
            stage_traces,
            CompressibilityScoringError,
        )

        prioritized = await _run_stage(
            "prioritize",
            len(scored),
            lambda: self._prioritizer.prioritize(scored, plan, config),
            stage_traces,
            PrioritizationError,
        )

        total_latency_ms = (time.perf_counter() - started) * 1000.0
        trace = OrchestratorTrace(
            stages=stage_traces,
            total_latency_ms=total_latency_ms,
            dedup_method_used=dedup_method,
            expansion_enabled=config.expansion_enabled,
        )

        try:
            pack = self._pack_assembler.assemble(
                items=prioritized,
                result=result,
                plan=plan,
                trace=trace,
                raw_input_token_count=raw_input_token_count,
                created_at=created_at,
            )
        except Exception as exc:  # noqa: BLE001
            raise PackagingError(str(exc)) from exc

        package_trace = OrchestratorStageTrace(
            stage="package",
            input_count=len(prioritized),
            output_count=len(prioritized),
            latency_ms=0.0,
        )
        trace = trace.model_copy(
            update={"stages": [*stage_traces, package_trace]}
        )
        pack = pack.model_copy(update={"trace": trace})

        logger.info(
            "orchestrate_complete plan_id=%s item_count=%d raw_candidate_count=%d "
            "total_latency_ms=%.2f schema_version=%s",
            plan.metadata.plan_id,
            len(pack.items),
            pack.raw_candidate_count,
            total_latency_ms,
            SCHEMA_VERSION,
        )
        return pack


async def _run_stage(
    stage: str,
    input_count: int,
    fn: Callable[[], Awaitable[T]],
    traces: list[OrchestratorStageTrace],
    error_cls: type[Exception],
) -> T:
    started = time.perf_counter()
    try:
        output = await fn()
    except error_cls:
        raise
    except Exception as exc:  # noqa: BLE001
        raise error_cls(str(exc)) from exc
    latency_ms = (time.perf_counter() - started) * 1000.0
    output_count = len(output) if isinstance(output, list) else input_count
    traces.append(
        OrchestratorStageTrace(
            stage=stage,  # type: ignore[arg-type]
            input_count=input_count,
            output_count=output_count,
            latency_ms=latency_ms,
        )
    )
    return output
