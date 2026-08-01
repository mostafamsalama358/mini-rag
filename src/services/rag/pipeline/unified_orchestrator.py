"""Unified SpecKit stage-graph orchestrator (spec 015)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from models.db_schemes import Project
from services.FieldRegistry import FieldProfile
from services.rag.adapters.field_context import FieldContextAdapter
from services.rag.adapters.vector_retriever import resolve_collection_name
from services.rag.pipeline.models import (
    PipelineExecutionContext,
    PipelineOutcome,
    PipelineStageTrace,
    UnifiedPipelineResult,
)
from services.rag.pipeline.telemetry import append_stage_trace

logger = logging.getLogger("uvicorn.error")

_STAGE_ORDER = ("parse", "plan", "retrieve", "evidence", "context", "answer")


class UnifiedRagOrchestrator:
    """Parse → plan → retrieve → evidence → context → answer."""

    def __init__(
        self,
        *,
        query_parse_service: Any,
        planner: Any,
        engine: Any,
        evidence_orchestrator: Any,
        context_builder: Any,
        answer_pipeline: Any,
        field_context_adapter: FieldContextAdapter | None = None,
        vectordb_client: Any = None,
        embedding_client: Any = None,
        db_client: Any = None,
    ) -> None:
        self._parse = query_parse_service
        self._planner = planner
        self._engine = engine
        self._evidence = evidence_orchestrator
        self._context = context_builder
        self._answer = answer_pipeline
        self._fields = field_context_adapter or FieldContextAdapter()
        self._vectordb = vectordb_client
        self._embedding = embedding_client
        self._db_client = db_client

    def _deadline_exceeded(self, ctx: PipelineExecutionContext) -> bool:
        return time.perf_counter() >= float(ctx.deadline_at)

    def _skip_remaining(
        self,
        traces: list[PipelineStageTrace],
        *,
        after_stage: str,
    ) -> None:
        seen = False
        for stage in _STAGE_ORDER:
            if stage == after_stage:
                seen = True
                continue
            if not seen:
                continue
            append_stage_trace(
                traces,
                stage=stage,  # type: ignore[arg-type]
                status="skipped",
                started_at=time.perf_counter(),
            )

    async def _build_retrieval_metadata(
        self,
        *,
        project: Project,
        ctx: PipelineExecutionContext,
        profile: FieldProfile,
        parse_result: Any,
        plan: Any,
    ) -> dict[str, Any]:
        from services.rag.answer_service import _get_project_field_manifest

        project_id = int(project.project_id)
        collection_name = resolve_collection_name(
            {"project_id": project_id},
            vectordb_client=self._vectordb,
            embedding_client=self._embedding,
        )
        query_plan = getattr(parse_result, "query_plan", None)
        entity = getattr(query_plan, "entity", None) if query_plan else None
        entities = list(getattr(query_plan, "entities", None) or []) if query_plan else []
        entity_prefixes: list[str] = []
        for raw in ([entity] if entity else []) + entities:
            text = str(raw or "").strip()
            if text and text not in entity_prefixes:
                entity_prefixes.append(text)
            if len(entity_prefixes) >= 8:
                break
        entity_prefix = entity_prefixes[0] if entity_prefixes else None
        if entity_prefix is None and plan is not None:
            plan_entities = getattr(plan, "entities", ()) or ()
            if plan_entities:
                for pe in plan_entities:
                    text = str(getattr(pe, "canonical_form", None) or "").strip()
                    if text and text not in entity_prefixes:
                        entity_prefixes.append(text)
                entity_prefix = entity_prefixes[0] if entity_prefixes else None

        max_candidates = None
        if plan is not None:
            limits = getattr(plan, "retrieval_limits", None)
            if limits is not None:
                max_candidates = getattr(limits, "max_candidates", None)

        field_manifest = None
        try:
            field_manifest = await _get_project_field_manifest(
                project_id,
                self._db_client,
                registry=getattr(profile, "field_registry", None),
            )
        except Exception:
            logger.debug("field_manifest_load_failed project_id=%s", project_id, exc_info=True)

        # metadata_filter may carry entity_key as the *name* of the entity
        # metadata column — strip it so it is not also applied as JSONB @>.
        metadata_filter = None
        entity_key = None
        if isinstance(ctx.metadata_filter, dict):
            metadata_filter = {
                k: v for k, v in ctx.metadata_filter.items() if k != "entity_key"
            }
            entity_key = ctx.metadata_filter.get("entity_key")
            if not metadata_filter:
                metadata_filter = None
        if not entity_key and field_manifest is not None:
            entity_key = getattr(field_manifest, "entity_key", None)
        # Leaflet / plain-text indexes store the value under metadata.entity.
        if entity_prefix and not entity_key:
            entity_key = "entity"

        field_key = getattr(query_plan, "field", None) if query_plan else None
        if field_key in (None, "", "unknown", "product_name"):
            field_key = None

        return {
            "collection_name": collection_name,
            "project_id": project_id,
            "entity": entity,
            "entity_prefix": entity_prefix,
            "entity_prefixes": entity_prefixes,
            "entity_key": entity_key,
            "field_key": field_key,
            "metadata_filter": metadata_filter,
            "limit": max_candidates or ctx.limit,
            "max_candidates": max_candidates or ctx.limit,
            "field_manifest": field_manifest,
            "field_registry": getattr(profile, "field_registry", None),
        }

    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict[str, Any] | None,
        profile: FieldProfile,
        ctx: PipelineExecutionContext,
    ) -> UnifiedPipelineResult:
        _ = limit, metadata_filter  # carried on ctx
        # --- parse ---
        stage_started = time.perf_counter()
        if self._deadline_exceeded(ctx):
            early_traces: list[PipelineStageTrace] = []
            append_stage_trace(
                early_traces, stage="parse", status="timed_out", started_at=stage_started
            )
            self._skip_remaining(early_traces, after_stage="parse")
            return UnifiedPipelineResult(
                execution_context=ctx,
                stage_traces=early_traces,
                outcome="timeout",
            )

        traces: list[PipelineStageTrace] = []
        result = UnifiedPipelineResult(
            execution_context=ctx,
            stage_traces=traces,
            outcome="error",
        )
        traces = result.stage_traces

        try:
            parse_result, _prior = await self._parse.parse(
                project=project,
                query=query,
                profile=profile,
                session_id=session_id,
            )
            result.parse_result = parse_result
            try:
                from services.rag.diagnostics import log_unified_parse

                log_unified_parse(
                    parse_result=parse_result,
                    domain=getattr(profile, "domain_key", None)
                    or getattr(getattr(profile, "field_registry", None), "domain_key", None),
                )
            except Exception:
                logger.debug("unified_parse_diagnostics_failed", exc_info=True)
            append_stage_trace(
                traces, stage="parse", status="completed", started_at=stage_started
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            append_stage_trace(
                traces,
                stage="parse",
                status="failed",
                started_at=stage_started,
                error_type=type(exc).__name__,
            )
            self._skip_remaining(traces, after_stage="parse")
            result.outcome = "error"
            return result

        query_plan = getattr(parse_result, "query_plan", None)
        if query_plan is not None and bool(getattr(query_plan, "needs_clarification", False)):
            self._skip_remaining(traces, after_stage="parse")
            result.outcome = "clarification"
            try:
                from services.rag.diagnostics import log_unified_outcome

                log_unified_outcome(outcome="clarification", answer_result=None)
            except Exception:
                pass
            return result

        # --- plan ---
        stage_started = time.perf_counter()
        if self._deadline_exceeded(ctx):
            append_stage_trace(
                traces, stage="plan", status="timed_out", started_at=stage_started
            )
            self._skip_remaining(traces, after_stage="plan")
            result.outcome = "timeout"
            return result

        try:
            planner_config = self._fields.build_planner_config(profile)
            plan = self._planner.plan(parse_result, planner_config)
            result.retrieval_plan = plan
            plan_id = getattr(getattr(plan, "metadata", None), "plan_id", None)
            try:
                from services.rag.diagnostics import log_unified_plan

                log_unified_plan(plan=plan)
            except Exception:
                logger.debug("unified_plan_diagnostics_failed", exc_info=True)
            append_stage_trace(
                traces,
                stage="plan",
                status="completed",
                started_at=stage_started,
                plan_id=plan_id,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            append_stage_trace(
                traces,
                stage="plan",
                status="failed",
                started_at=stage_started,
                error_type=type(exc).__name__,
            )
            self._skip_remaining(traces, after_stage="plan")
            result.outcome = "error"
            return result

        if bool(getattr(plan, "clarification_required", False)):
            self._skip_remaining(traces, after_stage="plan")
            result.outcome = "clarification"
            return result

        # --- retrieve ---
        stage_started = time.perf_counter()
        if self._deadline_exceeded(ctx):
            append_stage_trace(
                traces,
                stage="retrieve",
                status="timed_out",
                started_at=stage_started,
                plan_id=plan_id,
            )
            self._skip_remaining(traces, after_stage="retrieve")
            result.outcome = "timeout"
            return result

        try:
            policy = self._fields.build_engine_policy(ctx, profile)
            retrieval_metadata = await self._build_retrieval_metadata(
                project=project,
                ctx=ctx,
                profile=profile,
                parse_result=parse_result,
                plan=plan,
            )
            try:
                from services.rag.recommend.pipeline_hook import (
                    enrich_retrieval_metadata_for_recommend,
                )

                retrieval_metadata = enrich_retrieval_metadata_for_recommend(
                    retrieval_metadata, query_plan
                )
            except Exception:
                logger.debug("recommend_metadata_enrich_failed", exc_info=True)
            retrieval_result = await self._engine.execute(
                plan,
                policy,
                metadata=retrieval_metadata,
            )
            result.retrieval_result = retrieval_result
            candidates = getattr(retrieval_result, "candidates", ()) or ()
            try:
                from services.rag.recommend.pipeline_hook import (
                    is_recommend_plan,
                    run_recommend_decision,
                )
                from services.rag.diagnostics import log_recommend_decision

                if is_recommend_plan(query_plan):
                    decision, trace = run_recommend_decision(
                        query_plan=query_plan,
                        retrieval_candidates=list(candidates),
                        correlation_id=getattr(ctx, "request_id", None),
                    )
                    result.recommend_decision = decision
                    result.recommend_trace = trace
                    try:
                        log_recommend_decision(decision=decision, trace=trace)
                    except Exception:
                        logger.debug("recommend_diagnostics_failed", exc_info=True)
                    if decision is not None and decision.decision_type == "clarify":
                        if query_plan is not None and not getattr(
                            query_plan, "needs_clarification", False
                        ):
                            result.parse_result = parse_result.model_copy(
                                update={
                                    "query_plan": query_plan.model_copy(
                                        update={
                                            "needs_clarification": True,
                                            "clarification_prompt": decision.clarification_prompt,
                                        }
                                    )
                                }
                            ) if hasattr(parse_result, "model_copy") else parse_result
                        self._skip_remaining(traces, after_stage="retrieve")
                        result.outcome = "clarification"
                        return result
                    if decision is not None and decision.decision_type == "refuse":
                        # Continue to answer with refuse message via context/answer;
                        # do not invent candidates.
                        pass
            except Exception:
                logger.debug("recommend_decision_hook_failed", exc_info=True)
            try:
                from services.rag.diagnostics import log_unified_retrieval

                log_unified_retrieval(scope=retrieval_metadata, candidates=list(candidates))
            except Exception:
                logger.debug("unified_retrieval_diagnostics_failed", exc_info=True)
            append_stage_trace(
                traces,
                stage="retrieve",
                status="completed",
                started_at=stage_started,
                plan_id=plan_id,
                detail={
                    "candidate_count": len(candidates),
                    "entity_key": retrieval_metadata.get("entity_key"),
                    "entity_prefix": retrieval_metadata.get("entity_prefix"),
                    "field_key": retrieval_metadata.get("field_key"),
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            append_stage_trace(
                traces,
                stage="retrieve",
                status="failed",
                started_at=stage_started,
                plan_id=plan_id,
                error_type=type(exc).__name__,
            )
            self._skip_remaining(traces, after_stage="retrieve")
            result.outcome = "error"
            return result

        if not candidates:
            recommend_decision = getattr(result, "recommend_decision", None)
            dtype = getattr(recommend_decision, "decision_type", None)
            ordered = list(getattr(recommend_decision, "ordered_candidates", None) or [])
            if dtype == "clarify":
                self._skip_remaining(traces, after_stage="retrieve")
                result.outcome = "clarification"
                return result
            if dtype in ("refuse", "limited_coverage") or (
                dtype == "recommend" and ordered and not candidates
            ):
                # Pack-seeded recommend without retrieval hits: surface decision text
                # via a lightweight answer_result (frozen /answer content only).
                self._skip_remaining(traces, after_stage="retrieve")
                lang = getattr(query_plan, "language", "en") or "en"
                from core.answer_generation.composition.recommend_explanation_policy import (
                    medical_advice_disclaimer,
                )

                if dtype == "recommend" and ordered:
                    lines = []
                    for cand in ordered:
                        brand = cand.product_identity.product_line or cand.product_identity.brand
                        tags = ", ".join(cand.matched_indications) or "indication match"
                        lines.append(f"- {brand} ({tags})")
                    body = (
                        "خيارات من فهرس المشروع:\n" + "\n".join(lines)
                        if lang == "ar"
                        else "In-corpus options:\n" + "\n".join(lines)
                    )
                    body = body + "\n\n" + medical_advice_disclaimer(language=lang)
                else:
                    body = getattr(recommend_decision, "message", None) or (
                        "لا تتوفر توصية مناسبة."
                        if lang == "ar"
                        else "No suitable recommendation available."
                    )
                result.answer_result = type(
                    "AnswerResultLite",
                    (),
                    {
                        "answer": body,
                        "no_answer": False,
                        "needs_clarification": False,
                        "full_prompt": None,
                        "citations": [],
                    },
                )()
                result.outcome = "success" if dtype == "recommend" else "no_context"
                return result
            self._skip_remaining(traces, after_stage="retrieve")
            scoped = bool(
                retrieval_metadata.get("entity_prefix")
                or retrieval_metadata.get("field_key")
                or retrieval_metadata.get("entity_key")
            )
            result.outcome = "scope_miss" if scoped else "no_context"
            return result

        # --- evidence ---
        stage_started = time.perf_counter()
        if self._deadline_exceeded(ctx):
            append_stage_trace(
                traces,
                stage="evidence",
                status="timed_out",
                started_at=stage_started,
                plan_id=plan_id,
            )
            self._skip_remaining(traces, after_stage="evidence")
            result.outcome = "timeout"
            return result

        try:
            evidence_config = self._fields.build_evidence_config(profile)
            evidence_pack = await self._evidence.orchestrate(
                retrieval_result, plan, evidence_config
            )
            result.evidence_pack = evidence_pack
            append_stage_trace(
                traces,
                stage="evidence",
                status="completed",
                started_at=stage_started,
                plan_id=plan_id,
                detail={
                    "item_count": len(getattr(evidence_pack, "items", []) or []),
                    "is_empty": bool(getattr(evidence_pack, "is_empty", False)),
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            append_stage_trace(
                traces,
                stage="evidence",
                status="failed",
                started_at=stage_started,
                plan_id=plan_id,
                error_type=type(exc).__name__,
            )
            self._skip_remaining(traces, after_stage="evidence")
            result.outcome = "error"
            return result

        if bool(getattr(evidence_pack, "is_empty", False)) or not getattr(
            evidence_pack, "items", None
        ):
            self._skip_remaining(traces, after_stage="evidence")
            result.outcome = "no_context"
            return result

        # --- context ---
        stage_started = time.perf_counter()
        if self._deadline_exceeded(ctx):
            append_stage_trace(
                traces,
                stage="context",
                status="timed_out",
                started_at=stage_started,
                plan_id=plan_id,
            )
            self._skip_remaining(traces, after_stage="context")
            result.outcome = "timeout"
            return result

        try:
            context_config = self._fields.build_context_config(profile)
            built_context = await self._context.build(evidence_pack, context_config)
            result.built_context = built_context
            context_id = getattr(built_context, "context_id", None)
            blocks = getattr(built_context, "ordered_blocks", None) or []
            try:
                from services.rag.diagnostics import log_unified_context

                log_unified_context(built_context=built_context)
            except Exception:
                logger.debug("unified_context_diagnostics_failed", exc_info=True)
            append_stage_trace(
                traces,
                stage="context",
                status="completed",
                started_at=stage_started,
                plan_id=plan_id,
                context_id=context_id,
                detail={"block_count": len(blocks)},
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            append_stage_trace(
                traces,
                stage="context",
                status="failed",
                started_at=stage_started,
                plan_id=plan_id,
                error_type=type(exc).__name__,
            )
            self._skip_remaining(traces, after_stage="context")
            result.outcome = "error"
            return result

        if not blocks:
            self._skip_remaining(traces, after_stage="context")
            result.outcome = "no_context"
            return result

        # --- answer ---
        stage_started = time.perf_counter()
        if self._deadline_exceeded(ctx):
            append_stage_trace(
                traces,
                stage="answer",
                status="timed_out",
                started_at=stage_started,
                plan_id=plan_id,
                context_id=context_id,
            )
            result.outcome = "timeout"
            return result

        try:
            answer_config = self._fields.build_answer_config(profile)
            answer_result = await self._answer.run(
                context=built_context,
                question=query,
                config=answer_config,
            )
            result.answer_result = answer_result
            append_stage_trace(
                traces,
                stage="answer",
                status="completed",
                started_at=stage_started,
                plan_id=plan_id,
                context_id=context_id,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            append_stage_trace(
                traces,
                stage="answer",
                status="failed",
                started_at=stage_started,
                plan_id=plan_id,
                context_id=context_id,
                error_type=type(exc).__name__,
            )
            result.outcome = "error"
            return result

        outcome: PipelineOutcome = "success"
        if bool(getattr(answer_result, "needs_clarification", False)):
            outcome = "clarification"
        result.outcome = outcome
        try:
            from services.rag.diagnostics import log_unified_outcome

            log_unified_outcome(outcome=outcome, answer_result=answer_result)
        except Exception:
            logger.debug("unified_outcome_diagnostics_failed", exc_info=True)
        return result
