"""Build PipelineSnapshot for Answer Quality (014) offline evaluation."""

from __future__ import annotations

from typing import Any

from services.rag.pipeline.models import UnifiedPipelineResult


def build_pipeline_snapshot(result: UnifiedPipelineResult) -> dict[str, Any]:
    """Serialize a UnifiedPipelineResult into a snapshot suitable for IGoldenTestRunner."""
    answer_result = result.answer_result
    plan = result.retrieval_plan
    built = result.built_context
    pack = result.evidence_pack
    return {
        "request_id": result.execution_context.request_id,
        "project_id": result.execution_context.project_id,
        "outcome": result.outcome,
        "pipeline_version": result.execution_context.pipeline_version,
        "plan_id": getattr(plan, "plan_id", None) if plan is not None else None,
        "context_id": getattr(built, "context_id", None) if built is not None else None,
        "answer": getattr(answer_result, "answer", None) if answer_result is not None else None,
        "no_answer": bool(getattr(answer_result, "no_answer", False)) if answer_result else False,
        "citations": [
            c.model_dump() if hasattr(c, "model_dump") else dict(c)
            for c in (getattr(answer_result, "citations", None) or [])
        ],
        "evidence_item_count": len(getattr(pack, "items", []) or []) if pack is not None else 0,
        "stage_traces": [t.model_dump() for t in result.stage_traces],
    }
