"""Translate unified/legacy pipeline results to the frozen /answer API shape."""

from __future__ import annotations

from models.enums.ResponseEnums import ResponseSignal
from services.rag.pipeline.models import PipelineAnswerResponse, UnifiedPipelineResult


class ResponseAdapter:
    """Sole translator from internal pipeline types to PipelineAnswerResponse."""

    def from_legacy_tuple(
        self,
        answer: str | None,
        full_prompt: str | None,
        chat_history: list | None,
        needs_clarification: bool,
    ) -> PipelineAnswerResponse:
        signal = (
            ResponseSignal.RAG_CLARIFICATION_NEEDED
            if needs_clarification
            else ResponseSignal.RAG_ANSWER_SUCCESS
        )
        return PipelineAnswerResponse(
            answer=answer,
            full_prompt=full_prompt,
            chat_history=chat_history,
            needs_clarification=bool(needs_clarification),
            signal=signal,
        )

    def from_unified_result(
        self,
        result: UnifiedPipelineResult,
        *,
        original_query: str,
    ) -> PipelineAnswerResponse:
        _ = original_query  # reserved for future prompt reconstruction
        needs_clarification = result.outcome == "clarification"
        answer: str | None = None
        full_prompt: str | None = None
        chat_history: list | None = None

        answer_result = result.answer_result
        if answer_result is not None:
            answer = getattr(answer_result, "answer", None)
            if getattr(answer_result, "no_answer", False):
                # no_answer still carries explanatory text in answer field
                answer = answer or getattr(answer_result, "answer", None)
            composed = None
            if result.built_context is not None:
                composed = getattr(result.built_context, "prompt_text", None)
            full_prompt = composed
            needs_clarification = needs_clarification or bool(
                getattr(answer_result, "needs_clarification", False)
            )

        if result.outcome == "clarification" and not answer:
            parse_result = result.parse_result
            if parse_result is not None:
                plan = getattr(parse_result, "query_plan", None)
                if plan is not None:
                    answer = getattr(plan, "clarification_prompt", None) or answer
            if result.retrieval_plan is not None:
                answer = (
                    getattr(result.retrieval_plan, "clarification_prompt", None)
                    or getattr(result.retrieval_plan, "clarification_message", None)
                    or answer
                )
            if not answer:
                answer = (
                    "I could not map your question to a supported topic. "
                    "Please rephrase or name a specific item."
                )

        if result.outcome in ("no_context", "field_unavailable", "scope_miss") and not answer:
            answer = None

        if result.outcome == "timeout":
            signal = ResponseSignal.RAG_ANSWER_TIMEOUT
            if not answer:
                answer = (
                    "The answer request timed out while contacting embedding or "
                    "generation services. Please retry shortly."
                )
        elif result.outcome == "scope_miss":
            signal = ResponseSignal.RAG_SCOPE_MISS
        elif result.outcome in ("no_context", "field_unavailable"):
            signal = ResponseSignal.RAG_NO_CONTEXT
        elif needs_clarification or result.outcome == "clarification":
            signal = ResponseSignal.RAG_CLARIFICATION_NEEDED
            needs_clarification = True
        elif result.outcome == "error":
            signal = ResponseSignal.RAG_ANSWER_ERROR
        else:
            signal = ResponseSignal.RAG_ANSWER_SUCCESS

        return PipelineAnswerResponse(
            answer=answer,
            full_prompt=full_prompt,
            chat_history=chat_history,
            needs_clarification=needs_clarification,
            signal=signal,
        )
