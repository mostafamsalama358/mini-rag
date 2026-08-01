"""Extracted Skill-path helpers — shared by stages and legacy facades (022)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from core.field_resolution import assess_field_capability, resolve_from_plan
from core.query_parser.schema import ParseResult
from core.retrieval import (
    focus_document_text_for_query,
    ground_documents_to_entity,
    should_focus_document_text,
    sort_documents_for_prompt,
)
from helpers.config import get_settings
from models.db_schemes import Project
from repositories.chunk_repository import ChunkModel
from services.FieldRegistry import FieldProfile
from services.rag.answer_service import (
    RetrievalContext,
    _field_not_available_answer,
    _get_project_field_manifest,
    _grounding_entity_tokens,
    _no_context_answer,
)
from services.rag.diagnostics import (
    FallbackReason,
    capture_retrieval_scores,
    chunk_ids_from_documents,
    log_capability_check,
    log_fallback,
    log_generation_context,
    log_generation_result,
    log_no_retrieval_results,
    log_retrieval_results,
    resolve_search_mode,
)
from services.rag.embedding import EmbeddingCache
from services.rag.interaction_retrieval import fetch_interaction_documents
from services.rag.skills import get_retrieval_strategy, load_skill_prompt
from services.rag.skills.context import SkillExecutionContext
from services.rag.skills.filters import jsonb_metadata_filter, logical_field_key
from services.rag.skills.entity_parse import EntityParseResult
from utils.chunk_metadata import format_source_label
from utils.detect_language import detect_query_language
from utils.metrics import (
    RAG_GENERATION_LATENCY,
    RAG_NO_CONTEXT_TOTAL,
    RAG_PARSE_LATENCY,
    RAG_RETRIEVAL_DOCS,
    RAG_RETRIEVAL_LATENCY,
    RAG_RERANK_DOCS,
    RAG_RERANK_LATENCY,
    RAG_TOP_SCORE,
)
from utils.rag_response import parse_rag_answer
from utils.rerank import get_reranker

logger = logging.getLogger("uvicorn.error")

FetchPairFn = Callable[..., Awaitable[tuple[list, Any]]]
SearchVectorFn = Callable[[], Awaitable[Any]]


@dataclass(frozen=True)
class SkillRetrievalOutcome:
    documents: list
    retrieval_path: str
    rows_after_entity_filter: int


async def build_skill_retrieval_context(
    *,
    project: Project,
    metadata_filter: dict | None,
    limit: int,
    profile: FieldProfile,
    query_plan,
    skill_ctx: SkillExecutionContext,
    db_client,
) -> RetrievalContext:
    """Build retrieval hints for a Skill-bound QueryPlan."""
    settings = get_settings()
    field_manifest = await _get_project_field_manifest(
        int(project.project_id),
        db_client,
        registry=profile.field_registry,
    )
    field_resolution = resolve_from_plan(
        query_plan,
        profile.field_registry,
        field_manifest,
    )
    # Leaflet/txt corpora store logical fields in chunk metadata field_name,
    # not Excel column keys — fall back to Skill profile / plan field.
    if field_resolution is None or not getattr(field_resolution, "column_keys", ()):
        logical = logical_field_key(skill_ctx.metadata_filters) or (
            query_plan.field if query_plan.field and query_plan.field != "unknown" else None
        )
        if logical:
            from core.field_resolution import FieldResolution

            field_resolution = FieldResolution(
                concept=logical,
                column_keys=(logical,),
                output_shape=(
                    getattr(field_resolution, "output_shape", "prose")
                    if field_resolution is not None
                    else "prose"
                ),
                via="skill_profile_field",
            )
    field_is_list = bool(
        field_resolution is not None
        and getattr(field_resolution, "output_shape", "prose") == "list"
    )

    from core.field_resolution import resolve_entity_key

    entity_key = field_manifest.entity_key
    if not entity_key and field_manifest.columns:
        entity_key = resolve_entity_key(
            field_manifest,
            profile.field_registry,
            available_keys=set(field_manifest.columns.keys()),
        )
    # Leaflet chunks persist the brand under metadata key "entity".
    if not entity_key and query_plan.entity:
        entity_key = "entity"

    entity_prefix = None
    if query_plan.entity:
        entity_prefix = str(query_plan.entity).strip().upper() or None

    # Never apply Skill field/source lists as raw JSONB containment.
    entity_filter = dict(jsonb_metadata_filter(metadata_filter) or {})
    retrieval_limit = limit
    if query_plan.operation == "list" and query_plan.scope == "all":
        retrieval_limit = max(limit, int(profile.retrieval.exhaustive_min_limit))
    if field_is_list and query_plan.scope in ("all", "subset"):
        retrieval_limit = max(retrieval_limit, int(profile.retrieval.exhaustive_min_limit))
    if skill_ctx.prefers_exhaustive_retrieval:
        retrieval_limit = max(
            retrieval_limit,
            int(profile.retrieval.exhaustive_min_limit),
            500,
        )

    query_type = query_plan.field if query_plan.field != "unknown" else "factual"
    search_mode = resolve_search_mode(
        hybrid_enabled=bool(settings.RAG_ENABLE_HYBRID_SEARCH),
        field_resolution=field_resolution,
    )
    reranker_enabled = bool(getattr(settings, "RAG_ENABLE_RERANKER", False))

    return RetrievalContext(
        field_manifest=field_manifest,
        field_resolution=field_resolution,
        field_is_list=field_is_list,
        entity_key=entity_key,
        entity_prefix=entity_prefix,
        retrieval_limit=retrieval_limit,
        entity_filter=entity_filter,
        search_mode=search_mode,
        reranker_enabled=reranker_enabled,
        query_type=query_type,
    )


def build_parse_result(
    *,
    original_query: str,
    entity_result: EntityParseResult,
    skill_ctx: SkillExecutionContext,
) -> ParseResult:
    query_lang = detect_query_language(original_query, default="en")
    query_plan = skill_ctx.build_query_plan(language=query_lang)
    return ParseResult(
        original_query=original_query,
        canonical_query=entity_result.canonical_query or original_query,
        query_plan=query_plan,
        used_llm=entity_result.used_llm,
        latency_ms=entity_result.latency_ms,
        grounding_score=None,
        error=entity_result.error,
    )


async def retrieve_via_strategy(
    *,
    project: Project,
    project_label: str,
    parse_result: ParseResult,
    query_plan,
    profile: FieldProfile,
    retrieval: RetrievalContext,
    skill_ctx: SkillExecutionContext,
    nlp_controller,
    db_client,
) -> SkillRetrievalOutcome:
    """Strategy-plugin retrieval — callers MUST NOT branch on strategy name."""
    embedding_cache = EmbeddingCache()
    retrieval_start = time.time()
    default_path = (
        "entity_scoped" if retrieval.entity_key and retrieval.entity_prefix else "vector"
    )
    suppress_entity = skill_ctx.suppress_entity_scoped_search
    search_entity_key = (
        retrieval.entity_key if query_plan.entity and not suppress_entity else None
    )
    search_entity_prefix = (
        retrieval.entity_prefix if query_plan.entity and not suppress_entity else None
    )

    async def _search_vector() -> Any:
        return await nlp_controller.search_vector_db_collection(
            project=project,
            text=parse_result.canonical_query,
            limit=retrieval.retrieval_limit,
            metadata_filter=retrieval.entity_filter or None,
            profile=profile,
            embedding_cache=embedding_cache,
            field_resolution=retrieval.field_resolution,
            query_plan=query_plan,
            entity_key=search_entity_key,
            entity_prefix=search_entity_prefix,
        )

    async def _search_vector_unscoped_entity() -> Any:
        # Leaflet chunks often miss metadata.entity on field slices; retry with
        # field/semantic scope only so brand still matches via text embedding.
        return await nlp_controller.search_vector_db_collection(
            project=project,
            text=parse_result.canonical_query,
            limit=retrieval.retrieval_limit,
            metadata_filter=retrieval.entity_filter or None,
            profile=profile,
            embedding_cache=embedding_cache,
            field_resolution=retrieval.field_resolution,
            query_plan=query_plan,
            entity_key=None,
            entity_prefix=None,
        )

    async def _fetch_pair(*, entity: str) -> tuple[list, Any]:
        chunk_model = await ChunkModel.create_instance(db_client)
        return await fetch_interaction_documents(
            project_id=int(project.project_id),
            entity=entity,
            chunk_model=chunk_model,
            field_manifest=retrieval.field_manifest,
            registry=profile.field_registry,
            limit=retrieval.retrieval_limit,
        )

    strategy = get_retrieval_strategy(skill_ctx.retrieval_strategy)
    retrieved_documents, retrieval_path = await strategy.retrieve(
        ctx=skill_ctx,
        search_vector=_search_vector,
        fetch_pair_documents=_fetch_pair,
        default_path=default_path,
    )
    if (
        (not retrieved_documents)
        and search_entity_prefix
        and not skill_ctx.suppress_entity_scoped_search
    ):
        logger.info(
            "skill_entity_scope_empty_retry_unscoped skill_id=%s entity=%r field=%r",
            skill_ctx.skill_id,
            search_entity_prefix,
            query_plan.field,
        )
        retrieved_documents, retrieval_path = await strategy.retrieve(
            ctx=skill_ctx,
            search_vector=_search_vector_unscoped_entity,
            fetch_pair_documents=_fetch_pair,
            default_path="vector",
        )
        if retrieved_documents:
            retrieval_path = f"{retrieval_path}+entity_unscoped_retry"
    RAG_RETRIEVAL_LATENCY.labels(project_id=project_label).observe(
        time.time() - retrieval_start
    )

    if retrieved_documents is False:
        retrieved_documents = []

    return SkillRetrievalOutcome(
        documents=list(retrieved_documents),
        retrieval_path=retrieval_path,
        rows_after_entity_filter=len(retrieved_documents),
    )


def apply_document_grounding(
    *,
    retrieved_documents: list,
    query_plan,
    skill_ctx: SkillExecutionContext,
) -> tuple[list, int, list]:
    pre_grounding_count = len(retrieved_documents)
    pre_grounding_documents = list(retrieved_documents)
    if query_plan.entity and not skill_ctx.skip_entity_grounding:
        entity_tokens = _grounding_entity_tokens(query_plan.entity, [query_plan.entity])
        retrieved_documents = ground_documents_to_entity(
            retrieved_documents,
            entity_tokens=entity_tokens,
            related_tokens=[],
            related_only=False,
        )
    return retrieved_documents, pre_grounding_count, pre_grounding_documents


async def rerank_and_enrich_documents(
    *,
    project: Project,
    project_label: str,
    parse_result: ParseResult,
    query_plan,
    profile: FieldProfile,
    documents: list,
    entity_key: str | None,
    nlp_controller,
    db_client,
    reranker=None,
) -> list:
    settings = get_settings()
    structural_patterns = profile.structural_patterns
    documents = sort_documents_for_prompt(
        documents,
        parse_result.canonical_query,
        structural_patterns=structural_patterns,
    )

    active_reranker = reranker or get_reranker(settings)
    rerank_backend = (
        getattr(settings, "RAG_RERANKER_BACKEND", "unknown") or "unknown"
    ).lower()
    RAG_RERANK_DOCS.labels(project_id=project_label, backend=rerank_backend).observe(
        len(documents)
    )
    pre_rerank_scores = capture_retrieval_scores(documents)
    pre_rerank_count = len(documents)
    rerank_start = time.time()
    documents = await active_reranker.rerank(parse_result.canonical_query, documents)
    RAG_RERANK_LATENCY.labels(project_id=project_label, backend=rerank_backend).observe(
        time.time() - rerank_start
    )

    if pre_rerank_count > 0 and not documents:
        log_fallback(
            FallbackReason.RERANKER_REMOVED_ALL,
            retrieval_query=parse_result.canonical_query,
            entity=query_plan.entity,
            field=query_plan.field,
            pre_rerank_count=pre_rerank_count,
        )
        return []

    log_retrieval_results(
        documents,
        stage="post_rerank",
        plan_field=query_plan.field,
        entity_key=entity_key,
        pre_rerank_scores=pre_rerank_scores,
    )

    documents = await nlp_controller.enrich_retrieved_documents(
        project=project,
        documents=documents,
        db_client=db_client,
        query=parse_result.canonical_query,
        structural_patterns=structural_patterns,
    )

    RAG_RETRIEVAL_DOCS.labels(project_id=project_label).observe(len(documents))
    top_score = max((doc.score for doc in documents if doc.score is not None), default=0.0)
    RAG_TOP_SCORE.labels(project_id=project_label).observe(float(top_score))

    char_budget = int(getattr(settings, "RAG_PROMPT_CHAR_BUDGET", 0))
    if char_budget > 0 and documents:
        budget_filtered: list = []
        running_chars = 0
        for doc in documents:
            doc_chars = len(doc.text or "")
            if budget_filtered and running_chars + doc_chars > char_budget:
                break
            budget_filtered.append(doc)
            running_chars += doc_chars
        documents = budget_filtered or documents[:1]

    return documents


def document_text_for_prompt(text: str, query: str, profile: FieldProfile | None = None) -> str:
    chunk_text = text or ""
    if profile is not None and profile.retrieval.disable_chunk_focus:
        return chunk_text
    if should_focus_document_text(query):
        chunk_text = focus_document_text_for_query(chunk_text, query)
    return chunk_text


async def generate_skill_answer(
    *,
    project_label: str,
    original_query: str,
    parse_result: ParseResult,
    query_plan,
    profile: FieldProfile,
    skill_ctx: SkillExecutionContext,
    retrieved_documents: list,
    field_is_list: bool,
    generation_client,
    template_parser,
) -> tuple[str | None, str | None, list | None, bool]:
    """Generate answer using Skill-owned prompt and optional response schema."""
    settings = get_settings()
    previous_lang = template_parser.language
    query_lang = detect_query_language(
        original_query, default=getattr(template_parser, "default_language", "en")
    )
    template_parser.set_language(query_lang)
    full_prompt = None
    chat_history = None
    answer = None
    needs_clarification = False

    try:
        skill_prompt = load_skill_prompt(
            skill_ctx.domain_key,
            skill_ctx.prompt_ref,
            variables={"query": original_query},
        )
        system_prompt_str = profile.prompts.get(query_lang)
        if skill_prompt:
            system_prompt = skill_prompt
        elif system_prompt_str:
            from string import Template

            system_prompt = Template(system_prompt_str).substitute({})
        else:
            system_prompt = template_parser.get("rag", "system_prompt")

        if skill_ctx.citation_policy:
            _citation_hints = {
                "strict": (
                    "Citation policy: strict — cite only retrieved document spans; "
                    "do not invent sources."
                ),
                "relaxed": (
                    "Citation policy: relaxed — prefer retrieved documents; "
                    "note uncertainty when evidence is thin."
                ),
                "leaflet_only": (
                    "Citation policy: leaflet_only — use leaflet/source documents only; "
                    "ignore non-leaflet context."
                ),
            }
            hint = _citation_hints.get(str(skill_ctx.citation_policy))
            if hint:
                system_prompt = f"{system_prompt}\n\n{hint}"

        documents_prompts = "\n".join(
            [
                template_parser.get(
                    "rag",
                    "document_prompt",
                    {
                        "doc_num": idx + 1,
                        "source_label": format_source_label(
                            doc.metadata,
                            lang=query_lang,
                            label_template=getattr(profile.metadata, "label_template", None),
                        ),
                        "chunk_text": generation_client.process_text(
                            document_text_for_prompt(
                                doc.text or "", original_query, profile
                            )
                        ),
                    },
                )
                for idx, doc in enumerate(retrieved_documents)
            ]
        )
        header_prompt = template_parser.get(
            "rag", "header_prompt", {"query": original_query}
        )
        is_exhaustive = field_is_list or (
            query_plan.operation == "list" and query_plan.scope == "all"
        )
        if skill_prompt:
            footer_prompt = (
                f"Answer from retrieved documents only.\n\n## Question:\n{original_query}\n\n## Answer:\n"
            )
        elif system_prompt_str and is_exhaustive:
            footer_prompt = (
                f"Answer with a list per system rules.\n\n## Question:\n{original_query}\n\n## Answer:\n"
            )
        elif system_prompt_str:
            footer_prompt = (
                f"Answer from retrieved documents only.\n\n## Question:\n{original_query}\n\n## Answer:\n"
            )
        else:
            footer_prompt = template_parser.get(
                "rag", "footer_prompt", {"query": original_query}
            )

        chat_history = [
            generation_client.construct_prompt(
                prompt=system_prompt,
                role=generation_client.enums.SYSTEM.value,
            )
        ]

        full_prompt = "\n".join([header_prompt, documents_prompts, footer_prompt])
        log_generation_context(
            context_length=len(full_prompt or ""),
            chunks_used=len(retrieved_documents),
            chunk_ids=chunk_ids_from_documents(retrieved_documents),
        )
        exhaustive_tokens = 4096
        if is_exhaustive:
            gen_cfg = profile.config.get("generation") or {}
            exhaustive_tokens = int(gen_cfg.get("exhaustive_max_output_tokens", 8192))

        generate_async = getattr(generation_client, "generate_text_async", None)
        generation_start = time.time()
        gen_kwargs: dict = {}
        if skill_ctx.response_schema:
            gen_kwargs["response_schema"] = skill_ctx.response_schema
        if settings.LLM_USE_ASYNC and generate_async is not None:
            raw_generated_answer = await generate_async(
                prompt=full_prompt,
                chat_history=chat_history,
                max_output_tokens=exhaustive_tokens if is_exhaustive else None,
                **gen_kwargs,
            )
        else:
            raw_generated_answer = generation_client.generate_text(
                prompt=full_prompt,
                chat_history=chat_history,
                max_output_tokens=exhaustive_tokens if is_exhaustive else None,
                **gen_kwargs,
            )
        RAG_GENERATION_LATENCY.labels(project_id=project_label).observe(
            time.time() - generation_start
        )
        answer, needs_clarification = parse_rag_answer(raw_generated_answer)
        if not answer or not str(answer).strip():
            log_generation_result(
                answer_generated=False,
                fallback_used=True,
                reason="GENERATOR_REFUSED",
            )
            log_fallback(
                FallbackReason.GENERATOR_REFUSED,
                retrieval_query=parse_result.canonical_query,
                entity=query_plan.entity,
                field=query_plan.field,
                chunks_used=len(retrieved_documents),
            )
        else:
            log_generation_result(
                answer_generated=True,
                fallback_used=needs_clarification,
                reason="clarification_requested" if needs_clarification else "ok",
            )
    finally:
        template_parser.set_language(previous_lang)

    return answer, full_prompt, chat_history, needs_clarification


def check_field_capability(
    *,
    project_label: str,
    original_query: str,
    parse_result: ParseResult,
    query_plan,
    profile: FieldProfile,
    field_manifest,
) -> str | None:
    """Return user-facing message when field is unavailable, else None."""
    capability = assess_field_capability(
        query_plan.field,
        profile.field_registry,
        field_manifest,
    )
    physical_column = capability.physical_columns[0] if capability.physical_columns else None
    log_capability_check(
        logical_field=query_plan.field,
        physical_column=physical_column,
        status=capability.status.upper() if capability.status != "unknown" else "UNKNOWN",
        available_fields=capability.available_field_labels,
    )
    if capability.status != "not_available":
        return None
    log_fallback(
        FallbackReason.FIELD_NOT_AVAILABLE,
        retrieval_query=parse_result.canonical_query,
        entity=query_plan.entity,
        field=query_plan.field,
        available_fields=list(capability.available_field_labels),
    )
    RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
    lang = detect_query_language(original_query, default="en")
    return _field_not_available_answer(
        original_query,
        logical_field=query_plan.field,
        available_fields=capability.available_field_labels,
        lang=lang,
    )


def no_context_message(original_query: str) -> str:
    lang = detect_query_language(original_query, default="en")
    return _no_context_answer(original_query, lang=lang)


def log_skill_parse(project_label: str, domain_key: str, entity_result: EntityParseResult) -> None:
    RAG_PARSE_LATENCY.labels(
        project_id=project_label,
        domain_key=domain_key,
        outcome="ok",
    ).observe(entity_result.latency_ms / 1000.0)


def log_skill_bound(
    project_label: str,
    skill_ctx: SkillExecutionContext,
) -> None:
    logger.info(
        "rag_skill_bound project_id=%s skill_id=%s profile_id=%s strategy=%s filters=%s",
        project_label,
        skill_ctx.skill_id,
        skill_ctx.profile.id,
        skill_ctx.retrieval_strategy,
        skill_ctx.metadata_filters,
    )
