from .BaseController import BaseController
from models.db_schemes import Project, DataChunk
from models.ChunkModel import ChunkModel
from models.db_schemes import RetrievedDocument
from stores.llm.LLMEnums import DocumentTypeEnum
from services.RAGService import RAGService
from utils.retrieval import (
    build_retrieval_expansion_queries,
    deduplicate_retrieved_documents,
    hybrid_rrf,
    is_comparison_query,
    is_detail_query,
    merge_retrieved_documents,
    needs_continuation_chunk,
    rerank_retrieved_documents,
    retrieval_limit_for_query,
    continuation_chunk_key,
    _source_key,
)
from utils.structural_split import (
    extract_structural_targets,
    is_structural_reference_query,
    starts_different_chapter,
    text_references_chapter,
    article_context_limit,
    collect_article_context_chunks,
)
from helpers.config import get_settings
from typing import List
import asyncio
import json

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, 
                 embedding_client, template_parser, reranker=None):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.reranker = reranker

    def create_collection_name(self, project_id: str):
        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()

    def _embed_query(self, text: str):
        """Embed a query using the sync embedding client (unchanged behavior)."""
        return self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value,
        )

    async def _embed_query_async(self, text: str):
        """Embed a query without blocking the event loop when an async
        embedding client is available (LLM_USE_ASYNC=true). Falls back to
        running the sync client in a worker thread otherwise.
        """
        embed_async = getattr(self.embedding_client, "embed_text_async", None)
        if embed_async is not None:
            return await embed_async(
                text=text,
                document_type=DocumentTypeEnum.QUERY.value,
            )
        # No async surface — offload the blocking sync call to a thread.
        return await asyncio.to_thread(
            self.embedding_client.embed_text,
            text=text,
            document_type=DocumentTypeEnum.QUERY.value,
        )
    
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
                                   do_reset: bool = False):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items
        texts = [ c.chunk_text for c in chunks ]
        metadata = [ c.chunk_metadata for c in  chunks]

        settings = get_settings()
        embed_async = getattr(self.embedding_client, "embed_text_async", None)
        if getattr(settings, "LLM_USE_ASYNC", False) and embed_async is not None:
            vectors = await embed_async(
                text=texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )
        else:
            vectors = self.embedding_client.embed_text(
                text=texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )

        # step3: create collection if not exists
        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        _ = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids,
            batch_size=settings.VECTOR_DB_INSERT_BATCH_SIZE,
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
    ):
        if not query_vector:
            if not query_text:
                return []
            settings = get_settings()
            if getattr(settings, "LLM_USE_ASYNC", False):
                vectors = await self._embed_query_async(query_text)
            else:
                vectors = self._embed_query(query_text)

            if not vectors or len(vectors) == 0:
                return []
            query_vector = vectors[0] if isinstance(vectors, list) else None

        if not query_vector:
            return []

        # Use filtered search when a metadata filter is provided and the
        # provider supports it; otherwise fall back to plain vector search.
        if metadata_filter and hasattr(self.vectordb_client, "search_by_vector_filtered"):
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
    ):
        """Retrieve candidate documents for *text* using hybrid dense + sparse search.

        Pipeline
        --------
        1. Embed query once.
        2. Run dense vector search and (optionally) sparse FTS concurrently,
           both respecting *metadata_filter* when provided.
        3. Fuse results with classical Reciprocal Rank Fusion (rank-only).
        4. Run expansion queries (detail / comparison / structural) and merge.
        5. Return the top candidates for downstream reranking + enrichment.
        """
        collection_name = self.create_collection_name(project_id=project.project_id)

        settings = get_settings()
        rrf_k = max(1, int(getattr(settings, "RAG_RRF_K", 60)))

        # Candidate window: both dense and sparse fetch this many documents.
        candidates = int(getattr(settings, "RAG_RETRIEVAL_CANDIDATES", 30)) or 30

        # Determine whether hybrid (dense + sparse) retrieval is enabled.
        # RAG_ENABLE_HYBRID_SEARCH takes precedence; fall back to legacy
        # RAG_ENABLE_BM25 for backward compatibility.
        hybrid_enabled = getattr(settings, "RAG_ENABLE_HYBRID_SEARCH", None)
        if hybrid_enabled is None:
            hybrid_enabled = getattr(settings, "RAG_ENABLE_BM25", False)

        # Embed the primary query once to avoid duplicate API calls later.
        if getattr(settings, "LLM_USE_ASYNC", False):
            vectors = await self._embed_query_async(text)
        else:
            vectors = self._embed_query(text)
        primary_query_vector = vectors[0] if isinstance(vectors, list) and vectors else None

        # ----------------------------------------------------------------
        # Stage 1: Concurrent dense + sparse retrieval with metadata
        # pre-filtering applied directly inside each search query.
        # ----------------------------------------------------------------
        dense_coro = self._vector_search(
            collection_name=collection_name,
            query_vector=primary_query_vector,
            fetch_limit=candidates,
            metadata_filter=metadata_filter,
        )

        sparse_coro = None
        if hybrid_enabled and hasattr(self.vectordb_client, "search_by_text"):
            if metadata_filter and hasattr(self.vectordb_client, "search_by_text_filtered"):
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
            (dense_results, sparse_results) = await asyncio.gather(dense_coro, sparse_coro)
            dense_results = dense_results or []
            sparse_results = sparse_results or []
        else:
            dense_results = await dense_coro
            dense_results = dense_results or []
            sparse_results = []

        if not dense_results and not sparse_results:
            return False

        # ----------------------------------------------------------------
        # Stage 2: Classical RRF fusion (rank-only, no score mixing).
        # ----------------------------------------------------------------
        primary_results = hybrid_rrf(
            dense_results,
            sparse_results,
            k=rrf_k,
            limit=candidates,
        )

        if not primary_results:
            return False

        # ----------------------------------------------------------------
        # Stage 3: Query expansion — generates sub-queries for detail,
        # comparison, and structural reference queries.  Expansion results
        # are fused using the enriched RRF (lexical + structural boosts)
        # which is better suited for domain-specific expansion scoring,
        # then merged back into the primary candidate pool.
        # ----------------------------------------------------------------
        expansion_queries = build_retrieval_expansion_queries(text)
        if not expansion_queries:
            return primary_results

        fetch_multiplier = max(1, int(getattr(settings, "RAG_RETRIEVAL_FETCH_MULTIPLIER", 3)))
        if is_detail_query(text) or is_comparison_query(text) or is_structural_reference_query(text):
            fetch_multiplier = max(fetch_multiplier, 5)
        expansion_fetch_limit = max(12, int(candidates // fetch_multiplier))

        expansion_coroutines = [
            self._vector_search(
                collection_name=collection_name,
                query_text=expansion_query,
                fetch_limit=expansion_fetch_limit,
                metadata_filter=metadata_filter,
            )
            for expansion_query in expansion_queries
        ]
        expansion_batches = await asyncio.gather(*expansion_coroutines)

        extra_results: list = []
        for batch in expansion_batches:
            if batch:
                extra_results.extend(batch)

        if not extra_results:
            return primary_results

        # Merge expansion results into the primary pool and re-rank.
        merged = merge_retrieved_documents(primary_results, extra_results)
        merged = rerank_retrieved_documents(merged, text, rrf_k=rrf_k)

        # Deduplicate to the candidate window size.
        effective_limit = retrieval_limit_for_query(text, default_limit=limit)
        return deduplicate_retrieved_documents(merged, limit=max(effective_limit, candidates))

    def _append_chunk_if_new(
        self,
        *,
        extras: list[RetrievedDocument],
        existing_keys: set[str],
        chunk,
        score: float,
    ) -> None:
        sibling_key = _source_key(chunk.chunk_metadata)
        if sibling_key and sibling_key in existing_keys:
            return

        if sibling_key:
            existing_keys.add(sibling_key)

        extras.append(
            RetrievedDocument(
                text=chunk.chunk_text,
                score=score,
                metadata=chunk.chunk_metadata,
            )
        )

    async def _expand_structural_context(
        self,
        *,
        project: Project,
        documents: list[RetrievedDocument],
        chunk_model: ChunkModel,
        query: str,
        existing_keys: set[str],
    ) -> list[RetrievedDocument]:
        targets = extract_structural_targets(query)
        if not targets["article_numbers"] and not targets["chapter_labels"]:
            return []

        extras: list[RetrievedDocument] = []
        seed_documents = sorted(documents, key=lambda item: item.score, reverse=True)[:5]
        asset_ids: set[int] = set()

        for document in seed_documents:
            metadata = document.metadata or {}
            asset_id = metadata.get("asset_id")
            if asset_id is None:
                continue
            try:
                asset_ids.add(int(asset_id))
            except (TypeError, ValueError):
                continue

        for asset_id_int in asset_ids:
            asset_chunks = await chunk_model.get_chunks_by_asset(
                project_id=project.project_id,
                asset_id=asset_id_int,
            )

            for article_number in targets["article_numbers"]:
                context_chunks = collect_article_context_chunks(
                    asset_chunks,
                    article_number,
                    max_chunks=article_context_limit(query),
                )
                for index, chunk in enumerate(context_chunks):
                    self._append_chunk_if_new(
                        extras=extras,
                        existing_keys=existing_keys,
                        chunk=chunk,
                        score=0.98 - index * 0.005,
                    )

            for document in seed_documents:
                metadata = document.metadata or {}
                if metadata.get("asset_id") != asset_id_int:
                    continue

                chunk_order = metadata.get("chunk_order")
                page = metadata.get("page")

                if page is not None:
                    try:
                        page_int = int(page)
                    except (TypeError, ValueError):
                        page_int = None

                    if page_int is not None:
                        for page_chunk in await chunk_model.get_chunks_by_asset_page(
                            project_id=project.project_id,
                            asset_id=asset_id_int,
                            page=page_int,
                        ):
                            self._append_chunk_if_new(
                                extras=extras,
                                existing_keys=existing_keys,
                                chunk=page_chunk,
                                score=max(document.score, 0.96),
                            )

                for chapter_label in targets["chapter_labels"]:
                    if chunk_order is None:
                        continue
                    if not text_references_chapter(document.text, chapter_label):
                        continue

                    start_order = int(chunk_order)
                    for offset in range(0, 12):
                        order = start_order + offset
                        sibling = await chunk_model.get_chunk_by_asset_order(
                            project_id=project.project_id,
                            asset_id=asset_id_int,
                            chunk_order=order,
                        )
                        if sibling is None:
                            break
                        if offset > 0 and starts_different_chapter(
                            sibling.chunk_text,
                            chapter_label,
                        ):
                            break
                        self._append_chunk_if_new(
                            extras=extras,
                            existing_keys=existing_keys,
                            chunk=sibling,
                            score=max(document.score, 0.95 - offset * 0.01),
                        )

        return extras

    async def enrich_retrieved_documents(
        self,
        *,
        project: Project,
        documents: list[RetrievedDocument],
        db_client,
        query: str = "",
    ) -> list[RetrievedDocument]:
        if not documents or db_client is None:
            return documents

        chunk_model = await ChunkModel.create_instance(db_client)
        existing_keys = {
            key
            for doc in documents
            if (key := _source_key(doc.metadata))
        }
        extras: list[RetrievedDocument] = []

        for document in documents:
            if not needs_continuation_chunk(document.text):
                continue

            continuation_key = continuation_chunk_key(document.metadata)
            if not continuation_key:
                continue

            asset_id, next_order = continuation_key
            sibling = await chunk_model.get_chunk_by_asset_order(
                project_id=project.project_id,
                asset_id=asset_id,
                chunk_order=next_order,
            )
            if sibling is None:
                continue

            self._append_chunk_if_new(
                extras=extras,
                existing_keys=existing_keys,
                chunk=sibling,
                score=max(document.score, 0.95),
            )

        if is_structural_reference_query(query):
            extras.extend(
                await self._expand_structural_context(
                    project=project,
                    documents=documents,
                    chunk_model=chunk_model,
                    query=query,
                    existing_keys=existing_keys,
                )
            )

        if not extras:
            return documents

        combined = list(documents) + extras
        return sorted(combined, key=lambda item: item.score, reverse=True)

    async def answer_rag_question(
        self,
        project: Project,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
        db_client=None,
        metadata_filter: dict | None = None,
    ):
        rag_service = RAGService(
            db_client=db_client,
            nlp_controller=self,
            generation_client=self.generation_client,
            template_parser=self.template_parser,
            reranker=self.reranker,
        )

        return await rag_service.answer_question(
            project=project,
            query=query,
            limit=limit,
            session_id=session_id,
            metadata_filter=metadata_filter,
        )

