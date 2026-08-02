"""Strategy-plugin retrieval stage — no strategy-name branching (022)."""

from __future__ import annotations

from typing import Any

from services.rag.skills.runtime_support import (
    apply_document_grounding,
    build_skill_retrieval_context,
    check_field_capability,
    no_context_message,
    retrieve_via_strategy,
)
from services.rag.skills.stages.contracts import StageResult
from services.rag.diagnostics import (
    FallbackReason,
    log_fallback,
    log_no_retrieval_results,
    log_post_filter,
    log_retrieval_results,
)
from services.rag.indexing_diagnostics import log_grounding_rejection, log_raw_vector_metadata
from services.rag.answer_service import _grounding_entity_tokens
from utils.metrics import RAG_NO_CONTEXT_TOTAL


class RetrievalStage:
    name = "retrieval"

    async def execute(self, ctx: Any, **kwargs: Any) -> StageResult:
        skill_ctx = kwargs.get("skill_ctx") or getattr(ctx, "skill_ctx", None)
        if skill_ctx is None:
            return StageResult(stage=self.name, status="failed", error="missing_skill_ctx")

        from services.rag.skills.runtime_support import build_parse_result

        project = kwargs["project"]
        profile = kwargs["profile"]
        original_query = kwargs["query"]
        limit = kwargs.get("limit", 12)
        metadata_filter = kwargs.get("metadata_filter")
        entity_result = kwargs["entity_result"]
        project_label = str(getattr(project, "project_id", "unknown"))
        nlp_controller = kwargs["nlp_controller"]
        db_client = kwargs.get("db_client")

        metadata_filter = skill_ctx.merge_client_filters(metadata_filter)
        parse_result = build_parse_result(
            original_query=original_query,
            entity_result=entity_result,
            skill_ctx=skill_ctx,
        )
        query_plan = parse_result.query_plan

        retrieval = await build_skill_retrieval_context(
            project=project,
            metadata_filter=metadata_filter,
            limit=limit,
            profile=profile,
            query_plan=query_plan,
            skill_ctx=skill_ctx,
            db_client=db_client,
        )

        unavailable = check_field_capability(
            project_label=project_label,
            original_query=original_query,
            parse_result=parse_result,
            query_plan=query_plan,
            profile=profile,
            field_manifest=retrieval.field_manifest,
        )
        if unavailable:
            return StageResult(
                stage=self.name,
                status="no_context",
                payload={"answer": unavailable, "needs_clarification": False},
            )

        outcome = await retrieve_via_strategy(
            project=project,
            project_label=project_label,
            parse_result=parse_result,
            query_plan=query_plan,
            profile=profile,
            retrieval=retrieval,
            skill_ctx=skill_ctx,
            nlp_controller=nlp_controller,
            db_client=db_client,
        )
        retrieved_documents = outcome.documents
        retrieval_path = outcome.retrieval_path
        rows_after_entity_filter = outcome.rows_after_entity_filter

        log_post_filter(rows_after_entity_filter=rows_after_entity_filter)

        if not retrieved_documents:
            log_no_retrieval_results(
                retrieval_query=parse_result.canonical_query,
                metadata_filter=retrieval.entity_filter or None,
                entity=query_plan.entity,
                field=query_plan.field,
                reason=FallbackReason.ZERO_RETRIEVAL_RESULTS.value,
            )
            log_fallback(
                FallbackReason.ZERO_RETRIEVAL_RESULTS,
                retrieval_query=parse_result.canonical_query,
                metadata_filter=retrieval.entity_filter or None,
                entity=query_plan.entity,
                field=query_plan.field,
                retrieval_path=retrieval_path,
            )
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            return StageResult(
                stage=self.name,
                status="no_context",
                payload={
                    "answer": no_context_message(original_query),
                    "needs_clarification": False,
                },
            )

        log_retrieval_results(
            retrieved_documents,
            stage=f"initial ({retrieval_path})",
            plan_field=query_plan.field,
            entity_key=retrieval.entity_key,
        )
        log_raw_vector_metadata(
            retrieved_documents,
            stage="pre_grounding",
            entity_key=retrieval.entity_key,
        )

        retrieved_documents, pre_grounding_count, pre_grounding_documents = apply_document_grounding(
            retrieved_documents=retrieved_documents,
            query_plan=query_plan,
            skill_ctx=skill_ctx,
        )

        if query_plan.entity and not skill_ctx.skip_entity_grounding:
            entity_tokens = _grounding_entity_tokens(query_plan.entity, [query_plan.entity])
            log_post_filter(
                rows_after_entity_filter=rows_after_entity_filter,
                rows_after_field_filter=len(retrieved_documents),
            )
            if not retrieved_documents:
                log_grounding_rejection(
                    pre_grounding_documents,
                    entity_tokens=entity_tokens,
                    entity_key=retrieval.entity_key,
                )
                grounding_reason = (
                    FallbackReason.NO_ENTITY_MATCH
                    if query_plan.entity
                    else FallbackReason.FILTER_REMOVED_ALL_RESULTS
                )
                log_no_retrieval_results(
                    retrieval_query=parse_result.canonical_query,
                    metadata_filter=retrieval.entity_filter or None,
                    entity=query_plan.entity,
                    field=query_plan.field,
                    reason=grounding_reason.value,
                )
                log_fallback(
                    grounding_reason,
                    retrieval_query=parse_result.canonical_query,
                    metadata_filter=retrieval.entity_filter or None,
                    entity=query_plan.entity,
                    field=query_plan.field,
                    pre_grounding_count=pre_grounding_count,
                )
                RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
                return StageResult(
                    stage=self.name,
                    status="no_context",
                    payload={
                        "answer": no_context_message(original_query),
                        "needs_clarification": False,
                    },
                )

            log_retrieval_results(
                retrieved_documents,
                stage="post_grounding",
                plan_field=query_plan.field,
                entity_key=retrieval.entity_key,
            )

        reranker = kwargs.get("reranker")
        from services.rag.skills.runtime_support import rerank_and_enrich_documents

        if not skill_ctx._retrieval_flag("fetch_all_transactions"):
            retrieved_documents = await rerank_and_enrich_documents(
                project=project,
                project_label=project_label,
                parse_result=parse_result,
                query_plan=query_plan,
                profile=profile,
                documents=retrieved_documents,
                entity_key=retrieval.entity_key,
                nlp_controller=nlp_controller,
                db_client=db_client,
                reranker=reranker,
                skill_ctx=skill_ctx,
            )

        if not retrieved_documents:
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            return StageResult(
                stage=self.name,
                status="no_context",
                payload={
                    "answer": no_context_message(original_query),
                    "needs_clarification": False,
                },
            )

        return StageResult(
            stage=self.name,
            status="completed",
            payload={
                "documents": retrieved_documents,
                "parse_result": parse_result,
                "query_plan": query_plan,
                "retrieval": retrieval,
                "retrieval_path": retrieval_path,
            },
        )
