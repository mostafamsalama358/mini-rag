"""
services/rag/answer_service.py — Answer Generation Service
===========================================================
.NET Equivalent: IAnswerService / RagOrchestrator

Orchestrates the RAG pipeline via the semantic query parser (004):
  parse → retrieve (QueryPlan) → rerank → enrich → generate.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

from repositories.chat_message_repository import ChatMessageModel
from models.db_schemes import Project
from helpers.config import get_settings
from utils.chunk_metadata import format_source_label
from utils.detect_language import detect_query_language
from utils.rag_history import select_chat_history_messages
from utils.rag_response import parse_rag_answer
from core.field_resolution import (
    FieldManifest,
    assess_field_capability,
    infer_manifest_from_col_keys,
    resolve_entity_key,
    resolve_from_plan,
)
from repositories.asset_repository import AssetModel
from repositories.chunk_repository import ChunkModel
from core.retrieval import (
    focus_document_text_for_query,
    ground_documents_to_entity,
    should_focus_document_text,
    sort_documents_for_prompt,
)
from services.FieldRegistry import FieldProfile, get_field_registry
from utils.metrics import (
    RAG_RETRIEVAL_COUNT,
    RAG_RETRIEVAL_LATENCY,
    RAG_GENERATION_LATENCY,
    RAG_RERANK_LATENCY,
    RAG_RERANK_DOCS,
    RAG_RETRIEVAL_DOCS,
    RAG_TOP_SCORE,
    RAG_NO_CONTEXT_TOTAL,
    RAG_CLARIFICATION_TOTAL,
    RAG_PARSE_LATENCY,
)
from services.rag.embedding import EmbeddingCache
from services.rag.interaction_retrieval import fetch_interaction_documents
from services.rag.diagnostics import (
    FallbackReason,
    capture_retrieval_scores,
    chunk_ids_from_documents,
    log_capability_check,
    log_entity_prefilter,
    log_fallback,
    log_generation_context,
    log_generation_result,
    log_no_retrieval_results,
    log_post_filter,
    log_query_plan,
    log_retrieval_request,
    log_retrieval_results,
    resolve_search_mode,
)
from services.rag.indexing_diagnostics import log_grounding_rejection, log_raw_vector_metadata
from utils.rerank import get_reranker

logger = logging.getLogger("uvicorn.error")

_field_manifest_cache: dict[int, FieldManifest] = {}


@dataclass(frozen=True)
class RetrievalContext:
    field_manifest: FieldManifest
    field_resolution: object | None
    field_is_list: bool
    entity_key: str | None
    entity_prefix: str | None
    retrieval_limit: int
    entity_filter: dict
    search_mode: str
    reranker_enabled: bool
    query_type: str


@dataclass(frozen=True)
class LegacyRetrievalOutcome:
    documents: list
    retrieval_path: str
    rows_after_entity_filter: int


# Backward-compatible alias during migration; prefer LegacyRetrievalOutcome.
RetrievalResult = LegacyRetrievalOutcome


def _entity_spelling_match(token: str, entity: str) -> bool:
    t = (token or "").strip().casefold()
    e = (entity or "").strip().casefold()
    if not t or not e:
        return False
    return t == e or t in e or e in t


def _grounding_entity_tokens(effective_entity: str, lexical_variants: list[str]) -> list[str]:
    tokens: list[str] = []
    for raw in (effective_entity, *(effective_entity or "").split()):
        if raw and raw not in tokens:
            tokens.append(raw)
    for variant in lexical_variants:
        tok = (variant or "").strip().split()[0]
        if tok and _entity_spelling_match(tok, effective_entity) and tok not in tokens:
            tokens.append(tok)
    return tokens


def _no_context_answer(query: str, *, lang: str) -> str:
    if (lang or "").lower().startswith("ar"):
        return (
            "لم أجد في المستندات المفهرسة معلومات كافية للإجابة على هذا السؤال. "
            "جرّب ذكر اسم دواء أو منتج محدد، أو أعد صياغة السؤال."
        )
    return (
        "I could not find enough information in the indexed documents to answer this question. "
        "Try naming a specific drug or product, or rephrase your question."
    )


def _field_not_available_answer(
    query: str,
    *,
    logical_field: str,
    available_fields: list[str] | tuple[str, ...],
    lang: str,
) -> str:
    fields_text = ", ".join(available_fields) if available_fields else "none detected"
    if (lang or "").lower().startswith("ar"):
        return (
            f"الحقل المطلوب ({logical_field}) غير متوفر في البيانات المفهرسة. "
            f"الحقول المتاحة: {fields_text}."
        )
    return (
        f"The requested field ({logical_field}) is not available in the indexed data. "
        f"Available fields: {fields_text}."
    )


async def _get_project_field_manifest(
    project_id: int,
    db_client,
    *,
    registry=None,
) -> FieldManifest:
    cached = _field_manifest_cache.get(project_id)
    if cached is not None and cached.columns:
        return cached

    manifest = FieldManifest()
    if db_client is not None:
        try:
            asset_model = await AssetModel.create_instance(db_client)
            payloads = await asset_model.get_project_field_manifests(project_id)
        except Exception:
            payloads = []
        for payload in payloads:
            cols = payload.get("columns") or {}
            for meta_key, header in cols.items():
                manifest.columns.setdefault(meta_key, header)
            if manifest.entity_key is None and payload.get("entity_key"):
                manifest.entity_key = payload["entity_key"]

        if not manifest.columns:
            try:
                chunk_model = await ChunkModel.create_instance(db_client)
                col_keys = await chunk_model.get_project_col_metadata_keys(project_id)
                if col_keys:
                    entity_hint = None
                    if registry is not None:
                        entity_hint = getattr(registry, "entity_key_hint", None)
                    legacy = infer_manifest_from_col_keys(col_keys, entity_hint=entity_hint)
                    manifest.columns.update(legacy.columns)
                    if not manifest.entity_key:
                        manifest.entity_key = legacy.entity_key
            except Exception:
                pass

        if manifest.columns and not manifest.entity_key and registry is not None:
            manifest.entity_key = resolve_entity_key(
                manifest,
                registry,
                available_keys=set(manifest.columns.keys()),
            )

    _field_manifest_cache[project_id] = manifest
    return manifest


class RAGService:

    def __init__(self, db_client, nlp_controller, generation_client, template_parser, reranker=None, field_registry=None):
        self.db_client = db_client
        self.nlp_controller = nlp_controller
        self.generation_client = generation_client
        self.template_parser = template_parser
        self.reranker = reranker
        self.field_registry = field_registry or get_field_registry()
        self._skill_runtime = None

    def set_skill_runtime(self, skill_runtime) -> None:
        self._skill_runtime = skill_runtime

    async def _run_parse_stage(
        self,
        *,
        project: Project,
        original_query: str,
        profile: FieldProfile,
        session_id: str | None,
    ):
        from services.rag.pipeline.query_parse_service import QueryParseService

        parse_service = QueryParseService(
            generation_client=self.generation_client,
            db_client=self.db_client,
        )
        return await parse_service.parse(
            project=project,
            query=original_query,
            profile=profile,
            session_id=session_id,
        )

    async def _build_retrieval_context(
        self,
        *,
        project: Project,
        metadata_filter: dict | None,
        limit: int,
        profile: FieldProfile,
        query_plan,
        settings,
    ) -> RetrievalContext:
        field_manifest = await _get_project_field_manifest(
            int(project.project_id),
            self.db_client,
            registry=profile.field_registry,
        )
        field_resolution = resolve_from_plan(
            query_plan,
            profile.field_registry,
            field_manifest,
        )
        field_is_list = bool(
            field_resolution is not None
            and getattr(field_resolution, "output_shape", "prose") == "list"
        )

        entity_key = field_manifest.entity_key
        if not entity_key and field_manifest.columns:
            entity_key = resolve_entity_key(
                field_manifest,
                profile.field_registry,
                available_keys=set(field_manifest.columns.keys()),
            )

        entity_prefix = None
        if query_plan.entity:
            entity_prefix = str(query_plan.entity).strip().upper() or None

        entity_filter = dict(metadata_filter or {})
        retrieval_limit = limit
        if query_plan.operation == "list" and query_plan.scope == "all":
            retrieval_limit = max(limit, int(profile.retrieval.exhaustive_min_limit))
        if field_is_list and query_plan.scope in ("all", "subset"):
            retrieval_limit = max(retrieval_limit, int(profile.retrieval.exhaustive_min_limit))

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

    async def _run_retrieval_stage(
        self,
        *,
        project: Project,
        project_label: str,
        parse_result,
        query_plan,
        profile: FieldProfile,
        retrieval: RetrievalContext,
    ) -> RetrievalResult:
        embedding_cache = EmbeddingCache()
        retrieval_start = time.time()
        composition_api_token: str | None = None
        default_path = (
            "entity_scoped" if retrieval.entity_key and retrieval.entity_prefix else "vector"
        )
        search_entity_key = retrieval.entity_key if query_plan.entity else None
        search_entity_prefix = retrieval.entity_prefix if query_plan.entity else None

        async def _search_vector():
            return await self.nlp_controller.search_vector_db_collection(
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

        async def _fetch_pair(*, entity: str):
            chunk_model = await ChunkModel.create_instance(self.db_client)
            return await fetch_interaction_documents(
                project_id=int(project.project_id),
                entity=entity,
                chunk_model=chunk_model,
                field_manifest=retrieval.field_manifest,
                registry=profile.field_registry,
                limit=retrieval.retrieval_limit,
            )

        from services.rag.skills import get_retrieval_strategy

        strategy = get_retrieval_strategy("default")
        retrieved_documents, retrieval_path = await strategy.retrieve(
            ctx=None,
            search_vector=_search_vector,
            fetch_pair_documents=_fetch_pair,
            default_path=default_path,
        )
        _ = composition_api_token

        RAG_RETRIEVAL_LATENCY.labels(project_id=project_label).observe(time.time() - retrieval_start)

        if retrieved_documents is False:
            retrieved_documents = []

        rows_after_entity_filter = len(retrieved_documents)
        return RetrievalResult(
            documents=retrieved_documents,
            retrieval_path=retrieval_path,
            rows_after_entity_filter=rows_after_entity_filter,
        )

    def _apply_document_grounding_stage(
        self,
        *,
        retrieved_documents: list,
        query_plan,
    ) -> tuple[list, int, list]:
        pre_grounding_count = len(retrieved_documents)
        pre_grounding_documents = list(retrieved_documents)
        if query_plan.entity:
            entity_tokens = _grounding_entity_tokens(query_plan.entity, [query_plan.entity])
            retrieved_documents = ground_documents_to_entity(
                retrieved_documents,
                entity_tokens=entity_tokens,
                related_tokens=[],
                related_only=False,
            )
        return retrieved_documents, pre_grounding_count, pre_grounding_documents

    async def answer_question(
        self,
        *,
        project: Project,
        query: str,
        limit: int = 12,
        session_id: str | None = None,
        metadata_filter: dict | None = None,
        profile: FieldProfile | None = None,
        skill_id: str | None = None,
    ) -> tuple[str | None, str | None, list | None, bool]:
        """Answer a user question using semantic parse → retrieval → generation."""
        if profile is None:
            profile = self.nlp_controller.build_profile_for_project(
                project,
                language=detect_query_language(query, default="en"),
            )

        project_label = str(getattr(project, "project_id", "unknown"))
        original_query = query
        settings = get_settings()

        from services.rag.pipeline.skill_orchestrator import profile_has_skills

        if profile_has_skills(profile) and self._skill_runtime is not None:
            return await self._skill_runtime.execute_as_legacy_tuple(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                skill_id=skill_id,
            )

        if profile_has_skills(profile):
            raise RuntimeError("Skill runtime not configured")

        if not settings.RAG_SEMANTIC_PARSER_ENABLED:
            lang = detect_query_language(original_query, default="en")
            if lang.startswith("ar"):
                msg = "محلل الاستعلام الدلالي معطّل. فعّل RAG_SEMANTIC_PARSER_ENABLED للمتابعة."
            else:
                msg = "Semantic query parser is disabled. Set RAG_SEMANTIC_PARSER_ENABLED=true to continue."
            return msg, None, None, False

        parse_result, prior_messages = await self._run_parse_stage(
            project=project,
            original_query=query,
            profile=profile,
            session_id=session_id,
        )
        query_plan = parse_result.query_plan
        outcome = (
            "clarify"
            if query_plan.needs_clarification
            else ("fallback" if parse_result.error else "ok")
        )
        RAG_PARSE_LATENCY.labels(
            project_id=project_label,
            domain_key=profile.domain_key,
            outcome=outcome,
        ).observe(parse_result.latency_ms / 1000.0)
        log_query_plan(parse_result)
        if query_plan.needs_clarification:
            RAG_CLARIFICATION_TOTAL.labels(project_id=project_label).inc()
            prompt = query_plan.clarification_prompt or _no_context_answer(
                original_query,
                lang=detect_query_language(original_query, default="en"),
            )
            return prompt, None, None, True

        # Stage 2: turn the QueryPlan into retrieval hints and field/entity filters.
        retrieval = await self._build_retrieval_context(
            project=project,
            metadata_filter=metadata_filter,
            limit=limit,
            profile=profile,
            query_plan=query_plan,
            settings=settings,
        )
        field_manifest = retrieval.field_manifest
        field_resolution = retrieval.field_resolution
        field_is_list = retrieval.field_is_list
        entity_key = retrieval.entity_key
        entity_prefix = retrieval.entity_prefix
        entity_filter = retrieval.entity_filter
        retrieval_limit = retrieval.retrieval_limit
        search_mode = retrieval.search_mode
        reranker_enabled = retrieval.reranker_enabled

        capability = assess_field_capability(
            query_plan.field,
            profile.field_registry,
            retrieval.field_manifest,
        )
        physical_column = capability.physical_columns[0] if capability.physical_columns else None
        log_capability_check(
            logical_field=query_plan.field,
            physical_column=physical_column,
            status=capability.status.upper() if capability.status != "unknown" else "UNKNOWN",
            available_fields=capability.available_field_labels,
        )
        if capability.status == "not_available":
            log_fallback(
                FallbackReason.FIELD_NOT_AVAILABLE,
                retrieval_query=parse_result.canonical_query,
                entity=query_plan.entity,
                field=query_plan.field,
                available_fields=list(capability.available_field_labels),
            )
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            lang = detect_query_language(original_query, default="en")
            return (
                _field_not_available_answer(
                    original_query,
                    logical_field=query_plan.field,
                    available_fields=capability.available_field_labels,
                    lang=lang,
                ),
                None,
                None,
                False,
            )

        # Entity scoping uses prefix SQL pre-filter — not exact JSONB containment.
        RAG_RETRIEVAL_COUNT.labels(
            project_id=project_label,
            query_type=retrieval.query_type,
        ).inc()

        candidate_rows: int | None = None
        if retrieval.entity_key and retrieval.entity_prefix and self.db_client is not None:
            chunk_model = await ChunkModel.create_instance(self.db_client)
            candidate_rows = await chunk_model.count_entity_prefix_matches(
                int(project.project_id),
                entity_key=retrieval.entity_key,
                entity_prefix=retrieval.entity_prefix,
            )
        log_entity_prefilter(
            entity_key=retrieval.entity_key,
            entity_prefix=retrieval.entity_prefix,
            metadata_filter=retrieval.entity_filter or None,
            candidate_rows=candidate_rows,
        )

        log_retrieval_request(
            retrieval_query=parse_result.canonical_query,
            entity_id=query_plan.entity,
            entity_name=query_plan.entity,
            field=query_plan.field,
            metadata_filters=retrieval.entity_filter or None,
            top_k=retrieval.retrieval_limit,
            search_mode=retrieval.search_mode,
            reranker_enabled=retrieval.reranker_enabled,
            retrieval_path="entity_scoped" if retrieval.entity_key and retrieval.entity_prefix else "vector",
        )

        # Stage 3: strategy-driven retrieval (default strategy via registry).
        from services.rag.skills import get_retrieval_strategy

        embedding_cache = EmbeddingCache()
        retrieval_start = time.time()
        default_path = "entity_scoped" if entity_key and entity_prefix else "vector"
        search_entity_key = entity_key if query_plan.entity else None
        search_entity_prefix = entity_prefix if query_plan.entity else None

        async def _search_vector():
            return await self.nlp_controller.search_vector_db_collection(
                project=project,
                text=parse_result.canonical_query,
                limit=retrieval_limit,
                metadata_filter=entity_filter or None,
                profile=profile,
                embedding_cache=embedding_cache,
                field_resolution=field_resolution,
                query_plan=query_plan,
                entity_key=search_entity_key,
                entity_prefix=search_entity_prefix,
            )

        async def _fetch_pair(*, entity: str):
            chunk_model = await ChunkModel.create_instance(self.db_client)
            return await fetch_interaction_documents(
                project_id=int(project.project_id),
                entity=entity,
                chunk_model=chunk_model,
                field_manifest=field_manifest,
                registry=profile.field_registry,
                limit=retrieval_limit,
            )

        strategy = get_retrieval_strategy("default")
        retrieved_documents, retrieval_path = await strategy.retrieve(
            ctx=None,
            search_vector=_search_vector,
            fetch_pair_documents=_fetch_pair,
            default_path=default_path,
        )
        RAG_RETRIEVAL_LATENCY.labels(project_id=project_label).observe(time.time() - retrieval_start)

        if retrieved_documents is False:
            retrieved_documents = []

        rows_after_entity_filter = len(retrieved_documents)
        log_post_filter(rows_after_entity_filter=rows_after_entity_filter)

        if not retrieved_documents:
            log_no_retrieval_results(
                retrieval_query=parse_result.canonical_query,
                metadata_filter=entity_filter or None,
                entity=query_plan.entity,
                field=query_plan.field,
                reason=FallbackReason.ZERO_RETRIEVAL_RESULTS.value,
            )
            log_fallback(
                FallbackReason.ZERO_RETRIEVAL_RESULTS,
                retrieval_query=parse_result.canonical_query,
                metadata_filter=entity_filter or None,
                entity=query_plan.entity,
                field=query_plan.field,
                retrieval_path=retrieval_path,
            )
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            lang = detect_query_language(original_query, default="en")
            return _no_context_answer(original_query, lang=lang), None, None, False

        log_retrieval_results(
            retrieved_documents,
            stage=f"initial ({retrieval_path})",
            plan_field=query_plan.field,
            entity_key=entity_key,
        )
        log_raw_vector_metadata(
            retrieved_documents,
            stage="pre_grounding",
            entity_key=entity_key,
        )

        # Stage 4: ground the retrieved rows back to the committed entity.
        retrieved_documents, pre_grounding_count, pre_grounding_documents = self._apply_document_grounding_stage(
            retrieved_documents=retrieved_documents,
            query_plan=query_plan,
        )
        if query_plan.entity:
            entity_tokens = _grounding_entity_tokens(query_plan.entity, [query_plan.entity])
            log_post_filter(
                rows_after_entity_filter=rows_after_entity_filter,
                rows_after_field_filter=len(retrieved_documents),
            )
            if not retrieved_documents:
                log_grounding_rejection(
                    pre_grounding_documents,
                    entity_tokens=entity_tokens,
                    entity_key=entity_key,
                )
                grounding_reason = (
                    FallbackReason.NO_ENTITY_MATCH
                    if query_plan.entity
                    else FallbackReason.FILTER_REMOVED_ALL_RESULTS
                )
                log_no_retrieval_results(
                    retrieval_query=parse_result.canonical_query,
                    metadata_filter=entity_filter or None,
                    entity=query_plan.entity,
                    field=query_plan.field,
                    reason=grounding_reason.value,
                )
                log_fallback(
                    grounding_reason,
                    retrieval_query=parse_result.canonical_query,
                    metadata_filter=entity_filter or None,
                    entity=query_plan.entity,
                    field=query_plan.field,
                    pre_grounding_count=pre_grounding_count,
                )
                RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
                lang = detect_query_language(original_query, default="en")
                return _no_context_answer(original_query, lang=lang), None, None, False

            log_retrieval_results(
                retrieved_documents,
                stage="post_grounding",
                plan_field=query_plan.field,
                entity_key=entity_key,
            )

        structural_patterns = profile.structural_patterns
        retrieved_documents = sort_documents_for_prompt(
            retrieved_documents,
            parse_result.canonical_query,
            structural_patterns=structural_patterns,
        )

        reranker = self.reranker or get_reranker(settings)
        rerank_backend = (getattr(settings, "RAG_RERANKER_BACKEND", "unknown") or "unknown").lower()
        RAG_RERANK_DOCS.labels(project_id=project_label, backend=rerank_backend).observe(len(retrieved_documents))
        pre_rerank_scores = capture_retrieval_scores(retrieved_documents)
        pre_rerank_count = len(retrieved_documents)
        log_post_filter(
            rows_after_entity_filter=rows_after_entity_filter,
            rows_after_field_filter=pre_grounding_count if query_plan.entity else None,
            rows_sent_to_reranker=pre_rerank_count,
        )
        rerank_start = time.time()
        retrieved_documents = await reranker.rerank(parse_result.canonical_query, retrieved_documents)
        RAG_RERANK_LATENCY.labels(project_id=project_label, backend=rerank_backend).observe(time.time() - rerank_start)

        if pre_rerank_count > 0 and not retrieved_documents:
            log_fallback(
                FallbackReason.RERANKER_REMOVED_ALL,
                retrieval_query=parse_result.canonical_query,
                entity=query_plan.entity,
                field=query_plan.field,
                pre_rerank_count=pre_rerank_count,
            )
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            lang = detect_query_language(original_query, default="en")
            return _no_context_answer(original_query, lang=lang), None, None, False

        log_retrieval_results(
            retrieved_documents,
            stage="post_rerank",
            plan_field=query_plan.field,
            entity_key=entity_key,
            pre_rerank_scores=pre_rerank_scores,
        )

        retrieved_documents = await self.nlp_controller.enrich_retrieved_documents(
            project=project,
            documents=retrieved_documents,
            db_client=self.db_client,
            query=parse_result.canonical_query,
            structural_patterns=structural_patterns,
        )

        RAG_RETRIEVAL_DOCS.labels(project_id=project_label).observe(len(retrieved_documents))
        top_score = max((doc.score for doc in retrieved_documents if doc.score is not None), default=0.0)
        RAG_TOP_SCORE.labels(project_id=project_label).observe(float(top_score))

        log_retrieval_results(
            retrieved_documents,
            stage="post_enrich",
            plan_field=query_plan.field,
            entity_key=entity_key,
        )

        char_budget = int(getattr(settings, "RAG_PROMPT_CHAR_BUDGET", 0))
        if char_budget > 0 and retrieved_documents:
            budget_filtered: list = []
            running_chars = 0
            for doc in retrieved_documents:
                doc_chars = len(doc.text or "")
                if budget_filtered and running_chars + doc_chars > char_budget:
                    break
                budget_filtered.append(doc)
                running_chars += doc_chars
            retrieved_documents = budget_filtered or retrieved_documents[:1]

        if not retrieved_documents:
            log_fallback(
                FallbackReason.EMPTY_CONTEXT,
                retrieval_query=parse_result.canonical_query,
                entity=query_plan.entity,
                field=query_plan.field,
            )
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            lang = detect_query_language(original_query, default="en")
            return _no_context_answer(original_query, lang=lang), None, None, False

        previous_lang = self.template_parser.language
        query_lang = detect_query_language(query, default=getattr(self.template_parser, "default_language", "en"))
        self.template_parser.set_language(query_lang)
        full_prompt = None
        chat_history = None
        answer = None
        needs_clarification = False

        try:
            system_prompt_str = profile.prompts.get(query_lang)
            if system_prompt_str:
                from string import Template
                system_prompt = Template(system_prompt_str).substitute({})
            else:
                system_prompt = self.template_parser.get("rag", "system_prompt")

            documents_prompts = "\n".join([
                self.template_parser.get("rag", "document_prompt", {
                    "doc_num": idx + 1,
                    "source_label": format_source_label(
                        doc.metadata,
                        lang=query_lang,
                        label_template=getattr(profile.metadata, "label_template", None),
                    ),
                    "chunk_text": self.generation_client.process_text(
                        self._document_text_for_prompt(doc.text or "", original_query, profile)
                    ),
                })
                for idx, doc in enumerate(retrieved_documents)
            ])
            header_prompt = self.template_parser.get("rag", "header_prompt", {"query": original_query})
            is_exhaustive = field_is_list or (
                query_plan.operation == "list" and query_plan.scope == "all"
            )
            if system_prompt_str and is_exhaustive:
                footer_prompt = (
                    f"Answer with a list per system rules.\n\n## Question:\n{original_query}\n\n## Answer:\n"
                )
            elif system_prompt_str:
                footer_prompt = (
                    f"Answer from retrieved documents only.\n\n## Question:\n{original_query}\n\n## Answer:\n"
                )
            else:
                footer_prompt = self.template_parser.get("rag", "footer_prompt", {"query": original_query})

            chat_history = [
                self.generation_client.construct_prompt(
                    prompt=system_prompt,
                    role=self.generation_client.enums.SYSTEM.value,
                )
            ]

            if session_id and prior_messages:
                selected_messages = select_chat_history_messages(
                    prior_messages,
                    query=query,
                    mode=getattr(settings, "RAG_HISTORY_MODE", "auto"),
                    user_role=self.generation_client.enums.USER.value,
                )
                for message in selected_messages:
                    chat_history.append(
                        self.generation_client.construct_prompt(
                            prompt=message.content.get("text", ""),
                            role=message.role,
                        )
                    )

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

            generate_async = getattr(self.generation_client, "generate_text_async", None)
            generation_start = time.time()
            if settings.LLM_USE_ASYNC and generate_async is not None:
                raw_generated_answer = await generate_async(
                    prompt=full_prompt,
                    chat_history=chat_history,
                    max_output_tokens=exhaustive_tokens if is_exhaustive else None,
                )
            else:
                raw_generated_answer = self.generation_client.generate_text(
                    prompt=full_prompt,
                    chat_history=chat_history,
                    max_output_tokens=exhaustive_tokens if is_exhaustive else None,
                )
            RAG_GENERATION_LATENCY.labels(project_id=project_label).observe(time.time() - generation_start)
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
            self.template_parser.set_language(previous_lang)

        if needs_clarification:
            RAG_CLARIFICATION_TOTAL.labels(project_id=project_label).inc()

        if session_id and answer:
            chat_message_model = await ChatMessageModel.create_instance(self.db_client)
            await chat_message_model.create_chat_message(
                session_id=session_id,
                project_id=project.project_id,
                role=self.generation_client.enums.USER.value,
                content={"text": original_query},
            )
            await chat_message_model.create_chat_message(
                session_id=session_id,
                project_id=project.project_id,
                role=self.generation_client.enums.ASSISTANT.value,
                content={
                    "text": answer,
                    "query_plan": query_plan.model_dump(),
                    "canonical_query": parse_result.canonical_query,
                    "parse_latency_ms": parse_result.latency_ms,
                },
            )

        return answer, full_prompt, chat_history, needs_clarification

    def _document_text_for_prompt(self, text: str, query: str, profile: FieldProfile | None = None) -> str:
        chunk_text = text or ""
        if profile is not None and profile.retrieval.disable_chunk_focus:
            return chunk_text
        if should_focus_document_text(query):
            chunk_text = focus_document_text_for_query(chunk_text, query)
        return chunk_text
