from services.base import BaseController
from models.db_schemes import Project, DataChunk
from repositories.chunk_repository import ChunkModel
from models.db_schemes import RetrievedDocument
from models.enums.DomainKeyEnum import DomainKeyEnum
from stores.llm.LLMEnums import DocumentTypeEnum
from services.FieldRegistry import FieldProfile, FieldRegistry, get_field_registry
from services.rag.answer_service import RAGService
from core.retrieval import (
    build_retrieval_expansion_queries,
    deduplicate_retrieved_documents,
    hybrid_rrf,
    is_comparison_query,
    is_detail_query,
    merge_retrieved_documents,
    rerank_retrieved_documents,
    retrieval_limit_for_query,
)
from core.structural.engine import is_exhaustive_list_query, is_structural_reference_query
from services.rag.embedding import embed_primary_query, EmbeddingCache
from services.rag.enrichment import enrich_retrieved_documents
from services.rag.indexing_diagnostics import log_vector_insert_payload
from services.rag.metadata_enrichment import enrich_chunk_metadata
from helpers.config import get_settings
from typing import List
import asyncio
import json
import logging

logger = logging.getLogger("uvicorn.error")

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client,
                 embedding_client, template_parser, reranker=None,
                 field_registry: FieldRegistry | None = None):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.reranker = reranker
        self.field_registry = field_registry or get_field_registry()

    def build_profile_for_project(self, project: Project, *, language: str = "en") -> FieldProfile:
        domain_key = DomainKeyEnum.parse(getattr(project, "domain_key", None)).value
        config_json = getattr(project, "config_json", None) or {}
        # Project DB columns override pack defaults (FR-009). Pack prompts
        # remain available via FieldProfile.prompts when these are null.
        lang = (language or "en").lower()[:2]
        prompt_text = (
            getattr(project, "prompt_ar", None)
            if lang == "ar"
            else getattr(project, "prompt_en", None)
        ) or None
        return self.field_registry.build_profile(
            domain_key,
            project_overrides=config_json,
            language=language,
            prompt_text=prompt_text,
        )

    def create_collection_name(self, project_id: str):
        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()

    def _embed_query(self, text: str):
        """Embed a query using the sync embedding client (delegates to embedding.py)."""
        from services.rag.embedding import embed_query
        return embed_query(self.embedding_client, text)

    async def _embed_query_async(self, text: str):
        from services.rag.embedding import embed_query_async
        return await embed_query_async(self.embedding_client, text)

    async def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)

    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)

        if collection_info is None:
            return None

        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )

    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                                   chunks_ids: List[int],
                                   do_reset: bool = False,
                                   defer_index: bool = False) -> bool:
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items (enrich retrieval metadata before embed/insert)
        chunk_texts = [c.chunk_text for c in chunks]
        profile = self.build_profile_for_project(project)
        metadata = [
            enrich_chunk_metadata(
                c.chunk_metadata,
                c.chunk_text or "",
                enrichment=profile.metadata,
            )
            for c in chunks
        ]

        settings = get_settings()
        embed_async = getattr(self.embedding_client, "embed_text_async", None)
        if settings.LLM_USE_ASYNC and embed_async is not None:
            embedding_vectors = await embed_async(
                text=chunk_texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )
        else:
            embedding_vectors = self.embedding_client.embed_text(
                text=chunk_texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )

        if embedding_vectors is None:
            raise RuntimeError(
                "Embedding provider returned None (likely Vertex quota); "
                "refusing vector insert to avoid corrupt indexing"
            )
        if len(embedding_vectors) != len(chunk_texts):
            raise RuntimeError(
                f"Embedding count mismatch: vectors={len(embedding_vectors)} "
                f"texts={len(chunk_texts)}"
            )
        if any(v is None or len(v) == 0 for v in embedding_vectors):
            raise RuntimeError(
                "Embedding batch contained empty/None vectors; "
                "refusing vector insert"
            )

        # step3: create collection if not exists
        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        log_vector_insert_payload(
            collection_name=collection_name,
            chunk_ids=chunks_ids,
            metadata_batch=metadata,
            texts=chunk_texts,
        )
        _ = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=chunk_texts,
            metadata=metadata,
            vectors=embedding_vectors,
            record_ids=chunks_ids,
            batch_size=settings.VECTOR_DB_INSERT_BATCH_SIZE,
            create_index=not defer_index,
        )

        return True

    async def _vector_search(
        self,
        *,
        collection_name: str,
        fetch_limit: int,
        query_text: str | None = None,
        query_vector: list | None = None,
        metadata_filter: dict | None = None,
        embedding_cache: EmbeddingCache | None = None,
        entity_key: str | None = None,
        entity_prefix: str | None = None,
        field_key: str | None = None,
    ):
        if not query_vector:
            if not query_text:
                return []
            settings = get_settings()
            if settings.LLM_USE_ASYNC:
                from services.rag.embedding import embed_query_async
                vectors = await embed_query_async(
                    self.embedding_client,
                    query_text,
                    cache=embedding_cache,
                )
            else:
                from services.rag.embedding import embed_query
                if embedding_cache is not None:
                    cached = embedding_cache.get_vector(query_text)
                    if cached is not None:
                        vectors = [cached]
                    else:
                        vectors = embed_query(self.embedding_client, query_text)
                        if vectors and vectors[0] is not None:
                            embedding_cache.store_vector(query_text, vectors[0])
                else:
                    vectors = embed_query(self.embedding_client, query_text)

            if not vectors or len(vectors) == 0:
                return []
            query_vector = vectors[0] if isinstance(vectors, list) else None

        if not query_vector:
            return []

        scoped = (
            (entity_key and entity_prefix)
            or field_key
            or metadata_filter
        )
        if scoped and hasattr(self.vectordb_client, "search_by_vector_scoped"):
            results = await self.vectordb_client.search_by_vector_scoped(
                collection_name=collection_name,
                vector=query_vector,
                limit=fetch_limit,
                entity_key=entity_key,
                entity_prefix=entity_prefix,
                field_key=field_key,
                metadata_filter=metadata_filter,
            )
        elif metadata_filter and hasattr(self.vectordb_client, "search_by_vector_filtered"):
            results = await self.vectordb_client.search_by_vector_filtered(
                collection_name=collection_name,
                vector=query_vector,
                limit=fetch_limit,
                metadata_filter=metadata_filter,
            )
        else:
            results = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=query_vector,
                limit=fetch_limit,
            )
        return results or []

    async def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 10,
        metadata_filter: dict | None = None,
        profile: FieldProfile | None = None,
        query_variants: list[str] | None = None,
        _variants_only: bool = False,
        embedding_cache: EmbeddingCache | None = None,
        field_resolution=None,
        query_plan=None,
        entity_key: str | None = None,
        entity_prefix: str | None = None,
    ) -> list[RetrievedDocument] | bool:
        collection_name = self.create_collection_name(project_id=project.project_id)
        settings = get_settings()
        rrf_k = max(1, settings.RAG_RRF_K)
        candidates = settings.RAG_RETRIEVAL_CANDIDATES or 30

        if query_plan is not None and profile is not None:
            if query_plan.operation == "list" and query_plan.scope == "all":
                candidates = max(candidates, int(profile.retrieval.exhaustive_min_limit))
        elif profile is not None and is_exhaustive_list_query(text):
            candidates = max(candidates, int(profile.retrieval.exhaustive_min_limit))

        # When called in variants-only mode, skip the primary dense+sparse
        # search and jump straight to variant expansion over an empty pool.
        if _variants_only:
            return await self._run_expansion_and_merge(
                collection_name=collection_name,
                primary_results=[],
                text=text,
                metadata_filter=metadata_filter,
                limit=limit,
                candidates=candidates,
                rrf_k=rrf_k,
                settings=settings,
                structural_patterns=profile.structural_patterns if profile is not None else None,
                query_variants=query_variants,
                embedding_cache=embedding_cache,
                entity_key=entity_key,
                entity_prefix=entity_prefix,
                field_resolution=field_resolution,
            )

        hybrid_enabled = settings.RAG_ENABLE_HYBRID_SEARCH

        primary_query_vector = await embed_primary_query(
            self.embedding_client, text, cache=embedding_cache
        )

        dense_results, sparse_results = await self._fetch_dense_and_sparse_candidates(
            collection_name=collection_name,
            query_vector=primary_query_vector,
            text=text,
            metadata_filter=metadata_filter,
            candidates=candidates,
            hybrid_enabled=hybrid_enabled,
            field_resolution=field_resolution,
            entity_key=entity_key,
            entity_prefix=entity_prefix,
        )

        if not dense_results and not sparse_results:
            # Arabic brand queries often miss an English-only catalog on the
            # primary pass; still try configured alias / rewrite variants.
            if query_variants:
                return await self._run_expansion_and_merge(
                    collection_name=collection_name,
                    primary_results=[],
                    text=text,
                    metadata_filter=metadata_filter,
                    limit=limit,
                    candidates=candidates,
                    rrf_k=rrf_k,
                    settings=settings,
                    structural_patterns=profile.structural_patterns if profile is not None else None,
                    query_variants=query_variants,
                    embedding_cache=embedding_cache,
                    entity_key=entity_key,
                    entity_prefix=entity_prefix,
                    field_resolution=field_resolution,
                )
            return False

        primary_results = hybrid_rrf(
            dense_results,
            sparse_results,
            k=rrf_k,
            limit=candidates,
        )

        if not primary_results:
            if query_variants:
                return await self._run_expansion_and_merge(
                    collection_name=collection_name,
                    primary_results=[],
                    text=text,
                    metadata_filter=metadata_filter,
                    limit=limit,
                    candidates=candidates,
                    rrf_k=rrf_k,
                    settings=settings,
                    structural_patterns=profile.structural_patterns if profile is not None else None,
                    query_variants=query_variants,
                    embedding_cache=embedding_cache,
                    entity_key=entity_key,
                    entity_prefix=entity_prefix,
                    field_resolution=field_resolution,
                )
            return False

        from services.rag.indexing_diagnostics import log_raw_vector_metadata
        log_raw_vector_metadata(primary_results, stage="post_hybrid_rrf")

        return await self._run_expansion_and_merge(
            collection_name=collection_name,
            primary_results=primary_results,
            text=text,
            metadata_filter=metadata_filter,
            limit=limit,
            candidates=candidates,
            rrf_k=rrf_k,
            settings=settings,
            structural_patterns=profile.structural_patterns if profile is not None else None,
            query_variants=query_variants,
            embedding_cache=embedding_cache,
            entity_key=entity_key,
            entity_prefix=entity_prefix,
            field_resolution=field_resolution,
        )

    async def _fetch_dense_and_sparse_candidates(
        self,
        collection_name: str,
        query_vector: list | None,
        text: str,
        metadata_filter: dict | None,
        candidates: int,
        hybrid_enabled: bool,
        field_resolution=None,
        entity_key: str | None = None,
        entity_prefix: str | None = None,
    ) -> tuple[list, list]:
        field_key = None
        if field_resolution is not None and field_resolution.column_keys:
            field_key = field_resolution.column_keys[0]

        entity_scoped = bool(entity_key and entity_prefix)
        has_scoped = hasattr(self.vectordb_client, "search_by_vector_scoped")
        # extra.subject (and other JSONB filters) must stay applied when a Skill
        # also sets field_key. search_by_vector_field has no metadata_filter arg.
        use_scoped = bool((entity_scoped or metadata_filter) and has_scoped)

        if use_scoped:
            dense_coro = self.vectordb_client.search_by_vector_scoped(
                collection_name=collection_name,
                vector=query_vector,
                limit=candidates,
                entity_key=entity_key,
                entity_prefix=entity_prefix,
                field_key=field_key,
                metadata_filter=metadata_filter,
            )
        elif (
            field_key is not None
            and not entity_scoped
            and hasattr(self.vectordb_client, "search_by_vector_field")
        ):
            dense_coro = self.vectordb_client.search_by_vector_field(
                collection_name=collection_name,
                vector=query_vector,
                limit=candidates,
                field_key=field_key,
                field_value=None,
            )
        else:
            dense_coro = self._vector_search(
                collection_name=collection_name,
                query_vector=query_vector,
                fetch_limit=candidates,
                metadata_filter=metadata_filter,
                entity_key=entity_key,
                entity_prefix=entity_prefix,
                field_key=field_key,
            )

        sparse_coro = None
        if hybrid_enabled and hasattr(self.vectordb_client, "search_by_text"):
            if use_scoped and hasattr(self.vectordb_client, "search_by_text_scoped"):
                sparse_coro = self.vectordb_client.search_by_text_scoped(
                    collection_name=collection_name,
                    query=text,
                    limit=candidates,
                    entity_key=entity_key,
                    entity_prefix=entity_prefix,
                    field_key=field_key,
                    metadata_filter=metadata_filter,
                )
            elif field_key is not None and not entity_scoped and hasattr(self.vectordb_client, "search_by_text_field"):
                sparse_coro = self.vectordb_client.search_by_text_field(
                    collection_name=collection_name,
                    query=text,
                    limit=candidates,
                    field_key=field_key,
                    field_value=None,
                )
            elif metadata_filter and hasattr(self.vectordb_client, "search_by_text_filtered"):
                sparse_coro = self.vectordb_client.search_by_text_filtered(
                    collection_name=collection_name,
                    query=text,
                    limit=candidates,
                    metadata_filter=metadata_filter,
                )
            else:
                sparse_coro = self.vectordb_client.search_by_text(
                    collection_name=collection_name,
                    query=text,
                    limit=candidates,
                )

        if sparse_coro is not None:
            dense_results, sparse_results = await asyncio.gather(dense_coro, sparse_coro)
            dense_results = dense_results or []
            sparse_results = sparse_results or []
        else:
            dense_results = (await dense_coro) or []
            sparse_results = []

        if (
            field_key
            and metadata_filter
            and not dense_results
            and not sparse_results
            and has_scoped
        ):
            logger.info(
                "skill_field_soft_miss field_key=%r metadata_filter=%r",
                field_key,
                metadata_filter,
            )
            return await self._fetch_dense_and_sparse_candidates(
                collection_name=collection_name,
                query_vector=query_vector,
                text=text,
                metadata_filter=metadata_filter,
                candidates=candidates,
                hybrid_enabled=hybrid_enabled,
                field_resolution=None,
                entity_key=entity_key,
                entity_prefix=entity_prefix,
            )

        return dense_results, sparse_results

    async def _run_expansion_and_merge(
        self,
        collection_name: str,
        primary_results: list,
        text: str,
        metadata_filter: dict | None,
        limit: int,
        candidates: int,
        rrf_k: int,
        settings,
        structural_patterns=None,
        query_variants: list[str] | None = None,
        embedding_cache: EmbeddingCache | None = None,
        entity_key: str | None = None,
        entity_prefix: str | None = None,
        field_resolution=None,
    ):
        expansion_queries = build_retrieval_expansion_queries(text, structural_patterns=structural_patterns)

        # Merge configured expansion variants into the retrieval expansion set.
        if query_variants:
            seen = {q.lower() for q in expansion_queries}
            for variant in query_variants:
                key = variant.strip().lower()
                if key and key not in seen and key != text.strip().lower():
                    expansion_queries.append(variant.strip())
                    seen.add(key)

        if not expansion_queries:
            return primary_results

        fetch_multiplier = max(1, settings.RAG_RETRIEVAL_FETCH_MULTIPLIER)
        if is_detail_query(text) or is_comparison_query(text) or is_structural_reference_query(text, patterns=structural_patterns):
            fetch_multiplier = max(fetch_multiplier, 5)
        expansion_fetch_limit = max(12, int(candidates // fetch_multiplier))

        # Pre-embed all expansion texts in batched, serialized API calls so
        # asyncio.gather below only hits the vector DB (not Vertex in parallel).
        if embedding_cache is not None and expansion_queries:
            await embedding_cache.embed_many(self.embedding_client, expansion_queries)

        field_key = None
        if field_resolution is not None and field_resolution.column_keys:
            field_key = field_resolution.column_keys[0]

        expansion_coroutines = [
            self._vector_search(
                collection_name=collection_name,
                query_text=expansion_query,
                query_vector=(
                    embedding_cache.get_vector(expansion_query)
                    if embedding_cache is not None
                    else None
                ),
                fetch_limit=expansion_fetch_limit,
                metadata_filter=metadata_filter,
                embedding_cache=embedding_cache,
                entity_key=entity_key,
                entity_prefix=entity_prefix,
                field_key=field_key,
            )
            for expansion_query in expansion_queries
        ]

        # asyncio.gather is equivalent to Task.WhenAll
        expansion_batches = await asyncio.gather(*expansion_coroutines)

        extra_results: list = []
        for batch in expansion_batches:
            if batch:
                extra_results.extend(batch)

        if not extra_results:
            return primary_results

        # Merge expansion results into the primary pool and re-rank.
        merged_documents = merge_retrieved_documents(primary_results, extra_results)
        merged_documents = rerank_retrieved_documents(merged_documents, text, rrf_k=rrf_k, structural_patterns=structural_patterns)

        # Deduplicate to the candidate window size.
        effective_limit = retrieval_limit_for_query(text, default_limit=limit, structural_patterns=structural_patterns)
        return deduplicate_retrieved_documents(merged_documents, limit=max(effective_limit, candidates))

    async def enrich_retrieved_documents(
        self,
        *,
        project: Project,
        documents: list[RetrievedDocument],
        db_client,
        query: str = "",
        structural_patterns=None,
    ) -> list[RetrievedDocument]:
        """Enrich the reranked set; delegates continuation + structural context
        to services/rag/enrichment.py (extracted in 003 Phase 4c)."""
        if not documents or db_client is None:
            return documents
        chunk_model = await ChunkModel.create_instance(db_client)
        return await enrich_retrieved_documents(
            project=project,
            documents=documents,
            chunk_model=chunk_model,
            query=query,
            structural_patterns=structural_patterns,
        )

    async def answer_rag_question(
        self,
        project: Project,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
        db_client=None,
        metadata_filter: dict | None = None,
        pipeline_router=None,
        skill_id: str | None = None,
    ) -> tuple[str | None, str | None, list | None, bool, str | None]:
        from utils.detect_language import detect_query_language
        from models.enums.ResponseEnums import ResponseSignal

        query_lang = detect_query_language(query, default="en")
        profile = self.build_profile_for_project(project, language=query_lang)

        if pipeline_router is not None:
            response = await pipeline_router.execute(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                skill_id=skill_id,
            )
            # 5-tuple: answer, prompt, history, needs_clarification, signal
            return (
                response.answer,
                response.full_prompt,
                response.chat_history,
                response.needs_clarification,
                getattr(response.signal, "value", response.signal),
            )

        rag_service = RAGService(
            db_client=db_client,
            nlp_controller=self,
            generation_client=self.generation_client,
            template_parser=self.template_parser,
            reranker=self.reranker,
            field_registry=self.field_registry,
        )

        answer, full_prompt, chat_history, needs_clarification = await rag_service.answer_question(
            project=project,
            query=query,
            limit=limit,
            session_id=session_id,
            metadata_filter=metadata_filter,
            profile=profile,
            skill_id=skill_id,
        )
        signal = (
            ResponseSignal.RAG_CLARIFICATION_NEEDED.value
            if needs_clarification
            else ResponseSignal.RAG_ANSWER_SUCCESS.value
        )
        return answer, full_prompt, chat_history, needs_clarification, signal
