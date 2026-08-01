"""Adapt stage outputs to PipelineAnswerResponse fields (022)."""

from __future__ import annotations

from typing import Any

from models.enums.ResponseEnums import ResponseSignal
from services.rag.pipeline.models import PipelineAnswerResponse
from services.rag.skills.stages.contracts import StageResult


class FormattingStage:
    name = "formatting"

    async def execute(self, ctx: Any, **kwargs: Any) -> StageResult:
        answer = kwargs.get("answer")
        full_prompt = kwargs.get("full_prompt")
        chat_history = kwargs.get("chat_history")
        needs_clarification = bool(kwargs.get("needs_clarification", False))

        if needs_clarification:
            signal = ResponseSignal.RAG_CLARIFICATION_NEEDED
        elif answer:
            signal = ResponseSignal.RAG_ANSWER_SUCCESS
        else:
            signal = ResponseSignal.RAG_NO_CONTEXT

        response = PipelineAnswerResponse(
            answer=answer,
            full_prompt=full_prompt,
            chat_history=chat_history,
            needs_clarification=needs_clarification,
            signal=signal,
        )
        return StageResult(
            stage=self.name,
            status="completed",
            payload={"response": response},
        )

    @staticmethod
    def clarification_response(message: str | None) -> PipelineAnswerResponse:
        return PipelineAnswerResponse(
            answer=message,
            full_prompt=None,
            chat_history=None,
            needs_clarification=True,
            signal=ResponseSignal.RAG_CLARIFICATION_NEEDED,
        )

    @staticmethod
    def from_stage_payload(payload: dict[str, Any]) -> PipelineAnswerResponse:
        if "response" in payload:
            return payload["response"]
        return PipelineAnswerResponse(
            answer=payload.get("answer"),
            full_prompt=payload.get("full_prompt"),
            chat_history=payload.get("chat_history"),
            needs_clarification=bool(payload.get("needs_clarification", False)),
            signal=(
                ResponseSignal.RAG_CLARIFICATION_NEEDED
                if payload.get("needs_clarification")
                else (
                    ResponseSignal.RAG_ANSWER_SUCCESS
                    if payload.get("answer")
                    else ResponseSignal.RAG_NO_CONTEXT
                )
            ),
        )
