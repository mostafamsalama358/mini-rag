"""Retrieval Engine pipeline — execute RetrievalPlan → RetrievalResult."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from core.retrieval_engine.budget.enforcer import BudgetEnforcer
from core.retrieval_engine.errors import (
    InsufficientCandidatesError,
    RetrieverNotFoundError,
    SchemaMismatchError,
)
from core.retrieval_engine.interfaces import (
    IQueryExpander,
    IReranker,
    IRetrievalEngine,
    IScoreFuser,
)
from core.retrieval_engine.models import (
    EXPECTED_SCHEMA_MAJOR,
    SCHEMA_VERSION,
    ExpansionContext,
    FusionAlgorithm,
    RawCandidate,
    RetrievalContext,
    RetrievalEngineConfig,
    RetrievalExecutionMetadata,
    RetrievalQuery,
    RetrievalResult,
    RetrievedCandidate,
    RetrievalStepTrace,
    ScoreSource,
    compute_result_id,
)
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_engine.router import StrategyRouter
from core.retrieval_engine.tracing.tracer import RetrievalTracer
from core.retrieval_planner.models import RetrievalPlan

logger = logging.getLogger(__name__)


class RetrievalEnginePipeline(IRetrievalEngine):
    def __init__(
        self,
        *,
        expander: IQueryExpander,
        router: StrategyRouter,
        fuser: IScoreFuser,
        reranker: IReranker,
        budget_enforcer: BudgetEnforcer,
        tracer_factory: Callable[[], RetrievalTracer],
        config: RetrievalEngineConfig,
        default_policy: ExecutionPolicy | None = None,
    ) -> None:
        self._expander = expander
        self._router = router
        self._fuser = fuser
        self._reranker = reranker
        self._budget = budget_enforcer
        self._tracer_factory = tracer_factory
        self.config = config
        self._default_policy = default_policy or ExecutionPolicy()

    async def execute(
        self,
        plan: RetrievalPlan,
        policy: ExecutionPolicy | None = None,
        *,
        metadata: dict | None = None,
    ) -> RetrievalResult:
        started = time.perf_counter()
        active_policy = policy or self._default_policy
        tracer = self._tracer_factory()

        self._validate_schema(plan)

        context = RetrievalContext(
            plan_id=plan.metadata.plan_id,
            filters=plan.filters,
            constraints=plan.retrieval_constraints,
            hints=plan.execution_hints,
            policy=active_policy,
            metadata=dict(metadata or {}),
        )

        expansion_ctx = ExpansionContext(
            query_text=plan.canonical_query or "",
            intent_category=plan.intent.category,
            entities=tuple(e.canonical_form for e in plan.entities),
            language=(
                plan.retrieval_constraints.required_language
                if plan.retrieval_constraints
                else None
            ),
            max_variants=self.config.max_expander_variants,
        )
        expansion = self._expander.expand(expansion_ctx)
        variants = expansion.variants[: self.config.max_expander_variants]
        if not variants:
            variants = (plan.canonical_query or "",)

        had_hybrid = "hybrid" in plan.retrieval_strategies
        resolved = self._resolve_strategies(list(plan.retrieval_strategies))
        hybrid_components_used: tuple[str, ...] = (
            tuple(self.config.hybrid_components) if had_hybrid else ()
        )

        legs: list[tuple[str, str, str]] = []
        for strategy in resolved:
            for idx, variant_text in enumerate(variants):
                legs.append((strategy, variant_text, f"v{idx}"))

        leg_results: list[list[RawCandidate]] = []
        partial = False
        accumulated = 0

        if active_policy.cancellation.cancel_on_budget_exceeded and len(legs) > 1:
            for step_index, (strategy, variant_text, variant_id) in enumerate(legs):
                if accumulated >= plan.retrieval_limits.max_candidates:
                    tracer.append_step(
                        RetrievalStepTrace(
                            step_index=step_index,
                            strategy=strategy,
                            expander_variant_id=variant_id,
                            skipped=True,
                            skip_reason="budget_exhausted",
                        )
                    )
                    continue
                raw, step = await self._execute_leg(
                    step_index=step_index,
                    strategy=strategy,
                    variant_text=variant_text,
                    variant_id=variant_id,
                    context=context,
                    policy=active_policy,
                )
                tracer.append_step(step)
                if step.skipped and step.skip_reason == "timeout":
                    partial = True
                    tracer.record_violation(f"timeout on strategy={strategy}")
                if not step.skipped and step.error is None:
                    leg_results.append(raw)
                    accumulated += len(raw)
                elif step.error and not step.skipped:
                    partial = True
        else:
            tasks = [
                self._execute_leg(
                    step_index=i,
                    strategy=strategy,
                    variant_text=variant_text,
                    variant_id=variant_id,
                    context=context,
                    policy=active_policy,
                )
                for i, (strategy, variant_text, variant_id) in enumerate(legs)
            ]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for i, item in enumerate(gathered):
                strategy, _, variant_id = legs[i]
                if isinstance(item, BaseException):
                    partial = True
                    tracer.append_step(
                        RetrievalStepTrace(
                            step_index=i,
                            strategy=strategy,
                            expander_variant_id=variant_id,
                            skipped=True,
                            skip_reason="error",
                            error=str(item),
                        )
                    )
                    continue
                raw, step = item
                tracer.append_step(step)
                if step.skipped and step.skip_reason == "timeout":
                    partial = True
                    tracer.record_violation(f"timeout on strategy={strategy}")
                elif step.skipped and step.skip_reason == "retriever_not_found":
                    logger.warning(
                        "retriever_not_found plan_id=%s strategy=%s",
                        plan.metadata.plan_id,
                        strategy,
                    )
                if not step.skipped and step.error is None:
                    leg_results.append(raw)
                elif step.error and not step.skipped:
                    partial = True

        if not legs and not plan.clarification_required:
            # Empty strategy list without clarification — produce empty result.
            pass

        try:
            fused = self._fuser.fuse(leg_results) if leg_results else []
        except Exception as exc:  # noqa: BLE001
            logger.error("fusion_failed plan_id=%s error=%s", plan.metadata.plan_id, exc)
            fused = []
            partial = True
            tracer.record_violation(f"fusion_error: {exc}")

        capped = self._budget.apply_candidate_cap(fused, plan.retrieval_limits)

        score_source: ScoreSource = "fusion"
        reranker_used = self._reranker.reranker_id != "passthrough"
        reranked = capped
        if capped:
            try:
                timeout_s = (
                    active_policy.timeout.per_retriever_ms / 1000.0
                    if active_policy.timeout.per_retriever_ms
                    else None
                )
                if timeout_s is not None:
                    reranked = await asyncio.wait_for(
                        self._reranker.rerank(plan.canonical_query or "", capped),
                        timeout=timeout_s,
                    )
                else:
                    reranked = await self._reranker.rerank(
                        plan.canonical_query or "", capped
                    )
                if reranker_used:
                    score_source = "reranker"
            except asyncio.TimeoutError:
                partial = True
                tracer.record_violation("reranker_timeout")
                reranked = capped
                reranker_used = False
                score_source = "fusion"
                logger.warning(
                    "reranker_timeout plan_id=%s; using fusion order",
                    plan.metadata.plan_id,
                )

        if (
            len(resolved) == 1
            and len(variants) == 1
            and self._reranker.reranker_id == "passthrough"
            and score_source != "reranker"
        ):
            score_source = "raw"

        citation_required = bool(
            plan.retrieval_constraints and plan.retrieval_constraints.citation_required
        )
        retrieved = [
            RetrievedCandidate(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                score=float(c.raw_score),
                score_source=score_source,
                source_ref=c.source_ref
                if (c.source_ref is not None or not citation_required)
                else c.source_ref,
                content_excerpt=c.content_excerpt,
                rank=i,
            )
            for i, c in enumerate(reranked, start=1)
        ]
        evidence = self._budget.apply_evidence_cap(retrieved, plan.retrieval_limits)
        # Re-assign 1-based ranks after evidence cap.
        evidence = [
            c.model_copy(update={"rank": i}) for i, c in enumerate(evidence, start=1)
        ]

        total_latency_ms = (time.perf_counter() - started) * 1000.0
        if self._budget.check_latency_budget(
            total_latency_ms,
            plan.retrieval_constraints.latency_budget_ms
            if plan.retrieval_constraints
            else None,
        ):
            tracer.record_violation("latency_budget_exceeded")
            partial = True

        fusion_algorithm: FusionAlgorithm = (
            "rrf" if self._fuser.fuser_id == "rrf" else "passthrough"
        )
        expander_used = self._expander.expander_id != "passthrough"
        result_id = compute_result_id(
            plan.metadata.plan_id,
            resolved,
            fusion_algorithm,
            self._reranker.reranker_id,
        )
        metadata = RetrievalExecutionMetadata(
            result_id=result_id,
            plan_id=plan.metadata.plan_id,
            schema_version=SCHEMA_VERSION,
            executed_strategies=tuple(resolved),
            hybrid_components_used=hybrid_components_used,
            fusion_algorithm=fusion_algorithm,
            reranker_used=reranker_used,
            expander_used=expander_used,
            expander_type=self._expander.expansion_type,
            total_latency_ms=total_latency_ms,
        )
        trace = tracer.build_trace(plan.metadata.plan_id, total_latency_ms)

        pr = active_policy.partial_result
        if len(evidence) < pr.min_candidates_required:
            if not pr.allow_partial:
                raise InsufficientCandidatesError(
                    f"need {pr.min_candidates_required} candidates, got {len(evidence)}"
                )
            partial = True

        result = RetrievalResult(
            result_id=result_id,
            plan_id=plan.metadata.plan_id,
            candidates=tuple(evidence),
            trace=trace,
            metadata=metadata,
            partial=partial,
            schema_version=SCHEMA_VERSION,
        )

        log_fn = logger.warning if partial else logger.info
        log_fn(
            "retrieval_execute plan_id=%s strategies_executed=%s "
            "hybrid_components_used=%s candidate_count=%s reranker_used=%s "
            "expander_used=%s total_latency_ms=%.2f partial=%s",
            plan.metadata.plan_id,
            list(resolved),
            list(hybrid_components_used),
            len(evidence),
            reranker_used,
            expander_used,
            total_latency_ms,
            partial,
        )
        if self.config.trace_enabled:
            for step in trace.steps:
                logger.debug(
                    "retrieval_step plan_id=%s step=%s strategy=%s raw_count=%s "
                    "latency_ms=%.2f skipped=%s",
                    plan.metadata.plan_id,
                    step.step_index,
                    step.strategy,
                    step.raw_count,
                    step.latency_ms,
                    step.skipped,
                )
        return result

    def _resolve_strategies(self, strategies: list[str]) -> list[str]:
        resolved: list[str] = []
        for strategy in strategies:
            if strategy == "hybrid":
                resolved.extend(self.config.hybrid_components)
            else:
                resolved.append(strategy)
        return list(dict.fromkeys(resolved))

    def _validate_schema(self, plan: RetrievalPlan) -> None:
        version = plan.metadata.schema_version
        try:
            major = int(version.split(".")[0])
        except (ValueError, IndexError) as exc:
            logger.error("schema_mismatch invalid version=%s", version)
            raise SchemaMismatchError(f"invalid schema_version: {version!r}") from exc
        if major > EXPECTED_SCHEMA_MAJOR:
            logger.error("schema_mismatch version=%s", version)
            raise SchemaMismatchError(
                f"unsupported schema major {major} > {EXPECTED_SCHEMA_MAJOR}"
            )

    async def _execute_leg(
        self,
        *,
        step_index: int,
        strategy: str,
        variant_text: str,
        variant_id: str,
        context: RetrievalContext,
        policy: ExecutionPolicy,
    ) -> tuple[list[RawCandidate], RetrievalStepTrace]:
        leg_started = time.perf_counter()
        query = RetrievalQuery(
            query_text=variant_text,
            strategy=strategy,
            expander_variant_id=variant_id,
        )
        try:
            retriever = self._router.route(strategy)
        except RetrieverNotFoundError:
            return [], RetrievalStepTrace(
                step_index=step_index,
                strategy=strategy,
                expander_variant_id=variant_id,
                skipped=True,
                skip_reason="retriever_not_found",
            )
        except AssertionError:
            return [], RetrievalStepTrace(
                step_index=step_index,
                strategy=strategy,
                expander_variant_id=variant_id,
                skipped=True,
                skip_reason="invalid_strategy",
                error="hybrid must not reach router",
            )

        max_attempts = policy.retry.max_attempts
        retryable = set(policy.retry.retryable_on)
        last_error: str | None = None
        retry_count = 0
        timeout_s = (
            policy.timeout.per_retriever_ms / 1000.0
            if policy.timeout.per_retriever_ms
            else None
        )

        for attempt in range(max_attempts):
            try:
                if timeout_s is not None:
                    raw = await asyncio.wait_for(
                        retriever.retrieve(query, context),
                        timeout=timeout_s,
                    )
                else:
                    raw = await retriever.retrieve(query, context)
                latency_ms = (time.perf_counter() - leg_started) * 1000.0
                return raw, RetrievalStepTrace(
                    step_index=step_index,
                    strategy=strategy,
                    expander_variant_id=variant_id,
                    retriever_id=retriever.retriever_id,
                    raw_count=len(raw),
                    post_filter_count=len(raw),
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                )
            except asyncio.TimeoutError:
                latency_ms = (time.perf_counter() - leg_started) * 1000.0
                return [], RetrievalStepTrace(
                    step_index=step_index,
                    strategy=strategy,
                    expander_variant_id=variant_id,
                    retriever_id=retriever.retriever_id,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                    skipped=True,
                    skip_reason="timeout",
                    error="TimeoutError",
                )
            except Exception as exc:  # noqa: BLE001
                err_name = type(exc).__name__
                last_error = f"{err_name}: {exc}"
                if retryable and err_name not in retryable:
                    break
                if attempt < max_attempts - 1:
                    retry_count += 1
                    if policy.retry.backoff_ms > 0:
                        await asyncio.sleep(policy.retry.backoff_ms / 1000.0)
                    continue
                break

        latency_ms = (time.perf_counter() - leg_started) * 1000.0
        return [], RetrievalStepTrace(
            step_index=step_index,
            strategy=strategy,
            expander_variant_id=variant_id,
            retriever_id=retriever.retriever_id,
            latency_ms=latency_ms,
            retry_count=retry_count,
            skipped=True,
            skip_reason="error",
            error=last_error,
        )
