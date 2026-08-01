"""Structured DEBUG diagnostics for the post-parse RAG pipeline."""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from core.field_resolution import FieldResolution
from core.query_parser.schema import ParseResult
from helpers.config import get_settings
from models.db_schemes import RetrievedDocument
from utils.chunk_metadata import format_source_label

logger = logging.getLogger("uvicorn.error")

_SEPARATOR = "-" * 40


def _emit(message: str) -> None:
    """Log pipeline diagnostics at INFO when enabled, else DEBUG."""
    if get_settings().RAG_PIPELINE_DIAGNOSTICS:
        logger.info(message)
    else:
        logger.debug(message)


class FallbackReason(str, Enum):
    NO_ENTITY_MATCH = "NO_ENTITY_MATCH"
    ZERO_RETRIEVAL_RESULTS = "ZERO_RETRIEVAL_RESULTS"
    LOW_RELEVANCE_SCORE = "LOW_RELEVANCE_SCORE"
    FILTER_REMOVED_ALL_RESULTS = "FILTER_REMOVED_ALL_RESULTS"
    FIELD_NOT_AVAILABLE = "FIELD_NOT_AVAILABLE"
    EMPTY_CONTEXT = "EMPTY_CONTEXT"
    GENERATOR_REFUSED = "GENERATOR_REFUSED"
    RERANKER_REMOVED_ALL = "RERANKER_REMOVED_ALL"
    UNKNOWN = "UNKNOWN"


def resolve_search_mode(*, hybrid_enabled: bool, field_resolution: FieldResolution | None) -> str:
    field_aware = (
        field_resolution is not None
        and bool(field_resolution.column_keys)
    )
    if hybrid_enabled and field_aware:
        return "hybrid+field"
    if hybrid_enabled:
        return "hybrid"
    if field_aware:
        return "vector+field"
    return "vector"


def _preview(text: str | None, limit: int = 200) -> str:
    raw = (text or "").replace("\n", " ").strip()
    if len(raw) <= limit:
        return raw
    return raw[:limit] + "..."


def _format_filters(metadata_filter: dict | None) -> str:
    if not metadata_filter:
        return "{}"
    try:
        return json.dumps(metadata_filter, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return repr(metadata_filter)


def _chunk_key(doc: RetrievedDocument, index: int) -> str:
    meta = doc.metadata or {}
    for key in ("chunk_id", "record_id"):
        value = meta.get(key)
        if value is not None:
            return str(value)
    asset_id = meta.get("asset_id")
    chunk_order = meta.get("chunk_order")
    if asset_id is not None and chunk_order is not None:
        return f"{asset_id}:{chunk_order}"
    return f"idx:{index}"


from services.rag.indexing_diagnostics import extract_entity_from_metadata


def _chunk_entity(meta: dict | None, entity_key: str | None) -> str:
    return extract_entity_from_metadata(meta, entity_key)


def _chunk_field(meta: dict | None, plan_field: str | None) -> str:
    if plan_field and plan_field != "unknown":
        return plan_field
    if not meta:
        return ""
    for key in ("field", "concept", "column_header"):
        if meta.get(key) is not None:
            return str(meta[key])
    return ""


def log_query_plan(parse_result: ParseResult) -> None:
    plan = parse_result.query_plan
    lines = [
        _SEPARATOR,
        "QUERY PLAN",
        _SEPARATOR,
        f"original_query={parse_result.original_query!r}",
        f"canonical_query={parse_result.canonical_query!r}",
        f"entity={plan.entity!r}",
        f"field={plan.field!r}",
        f"operation={plan.operation!r}",
        f"scope={plan.scope!r}",
        f"language={plan.language!r}",
        f"needs_clarification={plan.needs_clarification}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_retrieval_request(
    *,
    retrieval_query: str,
    entity_id: str | None,
    entity_name: str | None,
    field: str,
    metadata_filters: dict | None,
    top_k: int,
    search_mode: str,
    reranker_enabled: bool,
    retrieval_path: str | None = None,
) -> None:
    lines = [
        _SEPARATOR,
        "RETRIEVAL REQUEST",
        _SEPARATOR,
        f"retrieval_query={retrieval_query!r}",
        f"entity_id={entity_id!r}",
        f"entity_name={entity_name!r}",
        f"field={field!r}",
        f"metadata_filter={_format_filters(metadata_filters)}",
        f"top_k={top_k}",
        f"search_mode={search_mode}",
        f"reranker_enabled={reranker_enabled}",
    ]
    if retrieval_path:
        lines.append(f"retrieval_path={retrieval_path}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_retrieval_results(
    documents: list[RetrievedDocument],
    *,
    stage: str,
    plan_field: str | None = None,
    entity_key: str | None = None,
    pre_rerank_scores: dict[str, float] | None = None,
) -> None:
    lines = [
        _SEPARATOR,
        f"RETRIEVAL RESULTS ({stage})",
        _SEPARATOR,
        f"chunks={len(documents)}",
    ]
    for idx, doc in enumerate(documents, start=1):
        meta = doc.metadata or {}
        doc_key = _chunk_key(doc, idx)
        document_name = format_source_label(meta, lang="en")
        entity = _chunk_entity(meta, entity_key)
        field = _chunk_field(meta, plan_field)
        retrieval_score = None
        if pre_rerank_scores is not None:
            retrieval_score = pre_rerank_scores.get(doc_key)
        rerank_score = doc.score if pre_rerank_scores is not None else None
        display_score = doc.score if pre_rerank_scores is None else retrieval_score

        lines.extend([
            "",
            f"[{idx}]",
            f"chunk_id={meta.get('chunk_id', doc_key)!r}",
            f"document_id={meta.get('asset_id')!r}",
            f"document_name={document_name!r}",
            f"entity={entity!r}",
            f"entity_key={entity_key!r}",
            f"has_fields_view={isinstance(meta.get('fields'), dict)}",
            f"field={field!r}",
            f"score={display_score}",
        ])
        if rerank_score is not None and pre_rerank_scores is not None:
            lines.append(f"rerank_score={rerank_score}")
        lines.append(f"preview={_preview(doc.text)!r}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_no_retrieval_results(
    *,
    retrieval_query: str,
    metadata_filter: dict | None,
    entity: str | None,
    field: str,
    reason: str | None = None,
) -> None:
    lines = [
        _SEPARATOR,
        "NO RETRIEVAL RESULTS",
        _SEPARATOR,
        f"retrieval_query={retrieval_query!r}",
        f"metadata_filter={_format_filters(metadata_filter)}",
        f"entity={entity!r}",
        f"field={field!r}",
    ]
    if reason:
        lines.append(f"reason={reason}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_generation_context(
    *,
    context_length: int,
    chunks_used: int,
    chunk_ids: list[str],
) -> None:
    lines = [
        _SEPARATOR,
        "GENERATION CONTEXT",
        _SEPARATOR,
        f"context_length={context_length}",
        f"chunks_used={chunks_used}",
        f"chunk_ids={chunk_ids!r}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_generation_result(
    *,
    answer_generated: bool,
    fallback_used: bool,
    reason: str = "",
) -> None:
    lines = [
        _SEPARATOR,
        "GENERATION RESULT",
        _SEPARATOR,
        f"answer_generated={answer_generated}",
        f"fallback_used={fallback_used}",
        f"reason={reason!r}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_fallback(reason: FallbackReason, **details: Any) -> None:
    payload = {key: value for key, value in details.items() if value is not None}
    lines = [
        _SEPARATOR,
        "FALLBACK RESPONSE",
        _SEPARATOR,
        f"reason={reason.value}",
    ]
    for key, value in sorted(payload.items()):
        if isinstance(value, (dict, list)):
            try:
                rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError):
                rendered = repr(value)
        else:
            rendered = repr(value)
        lines.append(f"{key}={rendered}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def chunk_ids_from_documents(documents: list[RetrievedDocument]) -> list[str]:
    return [_chunk_key(doc, idx) for idx, doc in enumerate(documents)]


def capture_retrieval_scores(documents: list[RetrievedDocument]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for idx, doc in enumerate(documents):
        scores[_chunk_key(doc, idx)] = float(doc.score) if doc.score is not None else 0.0
    return scores


def log_entity_prefilter(
    *,
    entity_key: str | None,
    entity_prefix: str | None,
    metadata_filter: dict | None,
    candidate_rows: int | None = None,
) -> None:
    lines = [
        _SEPARATOR,
        "ENTITY PRE-FILTER",
        _SEPARATOR,
        f"resolved_entity_key={entity_key!r}",
        f"entity_prefix={entity_prefix!r}",
        f"metadata_filter={_format_filters(metadata_filter)}",
    ]
    if candidate_rows is not None:
        lines.append(f"candidate_rows_before_ranking={candidate_rows}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_capability_check(
    *,
    logical_field: str,
    physical_column: str | None,
    status: str,
    available_fields: list[str] | tuple[str, ...] | None = None,
) -> None:
    lines = [
        _SEPARATOR,
        "CAPABILITY CHECK",
        _SEPARATOR,
        f"requested_logical_field={logical_field!r}",
        f"mapped_physical_column={physical_column!r}",
        f"capability_status={status!r}",
    ]
    if available_fields:
        lines.append(f"available_fields={list(available_fields)!r}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_post_filter(
    *,
    rows_after_entity_filter: int | None = None,
    rows_after_field_filter: int | None = None,
    rows_sent_to_reranker: int | None = None,
) -> None:
    lines = [
        _SEPARATOR,
        "POST FILTER",
        _SEPARATOR,
    ]
    if rows_after_entity_filter is not None:
        lines.append(f"rows_after_entity_filter={rows_after_entity_filter}")
    if rows_after_field_filter is not None:
        lines.append(f"rows_after_field_filter={rows_after_field_filter}")
    if rows_sent_to_reranker is not None:
        lines.append(f"rows_sent_to_reranker={rows_sent_to_reranker}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_unified_parse(*, parse_result: Any, domain: str | None = None) -> None:
    plan = getattr(parse_result, "query_plan", None)
    lines = [
        _SEPARATOR,
        "UNIFIED PARSE",
        _SEPARATOR,
        f"domain={domain!r}",
        f"original_query={getattr(parse_result, 'original_query', None)!r}",
        f"canonical_query={getattr(parse_result, 'canonical_query', None)!r}",
        f"entity={getattr(plan, 'entity', None)!r}",
        f"entities={list(getattr(plan, 'entities', None) or [])!r}",
        f"field={getattr(plan, 'field', None)!r}",
        f"operation={getattr(plan, 'operation', None)!r}",
        f"needs_clarification={bool(getattr(plan, 'needs_clarification', False))}",
        f"clarification_prompt={getattr(plan, 'clarification_prompt', None)!r}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_unified_plan(*, plan: Any) -> None:
    meta = getattr(plan, "metadata", None)
    strategies = getattr(plan, "retrieval_strategies", None) or ()
    lines = [
        _SEPARATOR,
        "UNIFIED PLAN",
        _SEPARATOR,
        f"plan_id={getattr(meta, 'plan_id', None)!r}",
        f"clarification_required={bool(getattr(plan, 'clarification_required', False))}",
        f"strategies={[getattr(s, 'strategy', s) for s in strategies]!r}",
        f"entity_count={len(getattr(plan, 'entities', ()) or ())}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_unified_retrieval(
    *,
    scope: dict[str, Any],
    candidates: list[Any],
    top_n: int = 8,
) -> None:
    lines = [
        _SEPARATOR,
        "UNIFIED RETRIEVAL",
        _SEPARATOR,
        f"entity_key={scope.get('entity_key')!r}",
        f"entity_prefix={scope.get('entity_prefix')!r}",
        f"entity_prefixes={scope.get('entity_prefixes')!r}",
        f"field_key={scope.get('field_key')!r}",
        f"metadata_filter={_format_filters(scope.get('metadata_filter'))}",
        f"candidate_count={len(candidates)}",
    ]
    for idx, cand in enumerate(list(candidates)[:top_n], start=1):
        excerpt = getattr(cand, "content_excerpt", None) or ""
        ref = getattr(cand, "source_ref", None)
        lines.extend(
            [
                "",
                f"[{idx}]",
                f"chunk_id={getattr(cand, 'chunk_id', None)!r}",
                f"document_id={getattr(cand, 'document_id', None)!r}",
                f"score={getattr(cand, 'score', getattr(cand, 'raw_score', None))}",
                f"strategy={getattr(cand, 'strategy', None)!r}",
                f"section_title={getattr(ref, 'section_title', None)!r}",
                f"preview={_preview(excerpt)!r}",
            ]
        )
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_unified_context(*, built_context: Any) -> None:
    blocks = getattr(built_context, "ordered_blocks", None) or []
    prompt = getattr(built_context, "prompt_text", None) or ""
    citation_map = getattr(built_context, "citation_map", None)
    lines = [
        _SEPARATOR,
        "UNIFIED CONTEXT",
        _SEPARATOR,
        f"context_id={getattr(built_context, 'context_id', None)!r}",
        f"block_count={len(blocks)}",
        f"prompt_chars={len(prompt)}",
        f"prompt_preview={_preview(prompt, limit=400)!r}",
        f"citation_keys={list(citation_map.keys()) if isinstance(citation_map, dict) else None!r}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_unified_outcome(*, outcome: str, answer_result: Any | None = None) -> None:
    answer = getattr(answer_result, "answer", None) if answer_result is not None else None
    lines = [
        _SEPARATOR,
        "UNIFIED OUTCOME",
        _SEPARATOR,
        f"outcome={outcome!r}",
        f"no_answer={bool(getattr(answer_result, 'no_answer', False)) if answer_result else None}",
        f"needs_clarification={bool(getattr(answer_result, 'needs_clarification', False)) if answer_result else None}",
        f"answer_preview={_preview(answer)!r}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_recommend_decision(*, decision: Any | None, trace: Any | None = None) -> None:
    """Feature 020 — recommend-mode decision + operator trace summary."""
    decision_type = getattr(decision, "decision_type", None) if decision else None
    candidates = list(getattr(decision, "ordered_candidates", None) or []) if decision else []
    trace_payload = None
    if trace is not None and hasattr(trace, "to_diagnostics"):
        try:
            trace_payload = trace.to_diagnostics()
        except Exception:
            trace_payload = None
    lines = [
        _SEPARATOR,
        "RECOMMEND DECISION",
        _SEPARATOR,
        f"decision_type={decision_type!r}",
        f"candidate_count={len(candidates)}",
        f"correlation_id={(trace_payload or {}).get('correlation_id')!r}",
        f"trace_candidates={json.dumps((trace_payload or {}).get('candidates') or [], ensure_ascii=False)[:1200]}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))
