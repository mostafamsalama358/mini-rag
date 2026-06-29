"""
services/RAGService.py — Answer Generation Service
===================================================
.NET Equivalent: IAnswerService / RagOrchestrator

This service orchestrates the entire Retrieval-Augmented Generation (RAG) pipeline:
  1. Retrieve raw candidate documents (Vector DB)
  2. Rerank candidates (Cross-encoder LLM)
  3. Enrich context (fetch neighboring chunks)
  4. Trim to fit token budget
  5. Construct the final prompt (System + Context + Chat History + Query)
  6. Generate the answer (Generation LLM)
"""
from models.ChatMessageModel import ChatMessageModel
from models.db_schemes import Project
from helpers.config import get_settings
from utils.chunk_metadata import format_source_label
from utils.detect_language import detect_query_language
from utils.rag_history import select_chat_history_messages
from utils.rag_response import parse_rag_answer
from utils.retrieval import (
    focus_document_text_for_query,
    is_comparison_query,
    is_detail_query,
    should_focus_document_text,
    sort_documents_for_prompt,
)
from utils.structural_split import (
    is_exhaustive_list_query,
    is_structural_reference_query,
)
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
)
from utils.rerank import get_reranker
import time


def _classify_query_type(query: str) -> str:
    if not query:
        return "unknown"
    if is_structural_reference_query(query):
        return "structural"
    if is_comparison_query(query):
        return "comparison"
    if is_exhaustive_list_query(query):
        return "exhaustive_list"
    if is_detail_query(query):
        return "detail"
    return "factual"


class RAGService:

    def __init__(self, db_client, nlp_controller, generation_client, template_parser, reranker=None):
        self.db_client = db_client
        self.nlp_controller = nlp_controller
        self.generation_client = generation_client
        self.template_parser = template_parser
        self.reranker = reranker

    async def answer_question(
        self,
        *,
        project: Project,
        query: str,
        limit: int = 12,
        session_id: str | None = None,
        metadata_filter: dict | None = None,
    ) -> tuple[str | None, str | None, list | None, bool]:
        """
        Main pipeline to answer a user's question using RAG.
        Returns a tuple of (answer, full_prompt, chat_history, needs_clarification).
        """
        answer, full_prompt, chat_history = None, None, None
        needs_clarification = False

        project_label = str(getattr(project, "project_id", "unknown"))
        query_type = _classify_query_type(query)
        RAG_RETRIEVAL_COUNT.labels(project_id=project_label, query_type=query_type).inc()

        retrieval_start = time.time()
        retrieved_documents = await self.nlp_controller.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
            metadata_filter=metadata_filter,
        )
        RAG_RETRIEVAL_LATENCY.labels(project_id=project_label).observe(time.time() - retrieval_start)

        if not retrieved_documents:
            RAG_NO_CONTEXT_TOTAL.labels(project_id=project_label).inc()
            return answer, full_prompt, chat_history, needs_clarification

        settings = get_settings()
        retrieved_documents = sort_documents_for_prompt(retrieved_documents, query)

        # Cross-encoder reranker runs on the candidate window BEFORE
        # enrichment so its capacity is spent on the most relevant base
        # candidates rather than continuation/context chunks.
        # (no-op when RAG_ENABLE_RERANKER=false)
        reranker = self.reranker or get_reranker(settings)
        rerank_backend = (getattr(settings, "RAG_RERANKER_BACKEND", "unknown") or "unknown").lower()
        RAG_RERANK_DOCS.labels(project_id=project_label, backend=rerank_backend).observe(
            len(retrieved_documents)
        )
        rerank_start = time.time()
        retrieved_documents = await reranker.rerank(query, retrieved_documents)
        RAG_RERANK_LATENCY.labels(project_id=project_label, backend=rerank_backend).observe(
            time.time() - rerank_start
        )

        # Enrich the reranked set with continuation chunks and structural
        # context — this expands only the documents that survived reranking.
        retrieved_documents = await self.nlp_controller.enrich_retrieved_documents(
            project=project,
            documents=retrieved_documents,
            db_client=self.db_client,
            query=query,
        )

        RAG_RETRIEVAL_DOCS.labels(project_id=project_label).observe(len(retrieved_documents))
        top_score = max(
            (doc.score for doc in retrieved_documents if doc.score is not None),
            default=0.0,
        )
        RAG_TOP_SCORE.labels(project_id=project_label).observe(float(top_score))

        # N3 — Token budget guard: drop lowest-ranked docs when the joined
        # context text would exceed RAG_PROMPT_CHAR_BUDGET characters.
        # Always keeps at least one document so the answer is grounded.
        char_budget = int(getattr(settings, "RAG_PROMPT_CHAR_BUDGET", 0))
        if char_budget > 0 and retrieved_documents:
            budget_filtered_docs: list = []
            running_chars = 0
            for doc in retrieved_documents:          # already sorted best-first
                doc_chars = len(doc.text or "")
                if budget_filtered_docs and running_chars + doc_chars > char_budget:
                    break
                budget_filtered_docs.append(doc)
                running_chars += doc_chars
            retrieved_documents = budget_filtered_docs or retrieved_documents[:1]

        previous_lang = self.template_parser.language
        query_lang = detect_query_language(
            query,
            default=getattr(self.template_parser, "default_language", "en"),
        )
        self.template_parser.set_language(query_lang)
        template_lang = query_lang

        try:
            # Equivalent to a C# 'try-finally' or 'using' statement.
            # Ensures the parser's language state is reset even if generation throws an error.
            system_prompt_str = None
            if project and getattr(project, "prompt_override", None):
                if template_lang == "ar" and project.prompt_override.prompt_ar:
                    from string import Template
                    system_prompt_str = Template(project.prompt_override.prompt_ar).substitute({})
                elif template_lang == "en" and project.prompt_override.prompt_en:
                    from string import Template
                    system_prompt_str = Template(project.prompt_override.prompt_en).substitute({})

            if system_prompt_str:
                system_prompt = system_prompt_str
            else:
                system_prompt = self.template_parser.get("rag", "system_prompt")


            documents_prompts = "\n".join([
                self.template_parser.get("rag", "document_prompt", {
                    "doc_num": idx + 1,
                    "source_label": format_source_label(doc.metadata, lang=template_lang),
                    "chunk_text": self.generation_client.process_text(
                        self._document_text_for_prompt(doc.text or "", query)
                    ),
                })
                for idx, doc in enumerate(retrieved_documents)
            ])

            header_prompt = self.template_parser.get("rag", "header_prompt", {
                "query": query,
            })
            footer_prompt = self.template_parser.get("rag", "footer_prompt", {
                "query": query,
            })

            chat_history = [
                self.generation_client.construct_prompt(
                    prompt=system_prompt,
                    role=self.generation_client.enums.SYSTEM.value,
                )
            ]

            if session_id:
                chat_message_model = await ChatMessageModel.create_instance(self.db_client)
                prior_messages = await chat_message_model.get_chat_history(
                    session_id=session_id,
                    project_id=project.project_id,
                )
                settings = get_settings()
                history_mode = getattr(settings, "RAG_HISTORY_MODE", "auto")
                selected_messages = select_chat_history_messages(
                    prior_messages,
                    query=query,
                    mode=history_mode,
                    user_role=self.generation_client.enums.USER.value,
                )

                for message in selected_messages:
                    chat_history.append(
                        self.generation_client.construct_prompt(
                            prompt=message.content.get("text", ""),
                            role=message.role,
                        )
                    )

            full_prompt = "\n\n".join([header_prompt, documents_prompts, footer_prompt])

            settings = get_settings()
            generate_async = getattr(self.generation_client, "generate_text_async", None)
            generation_start = time.time()
            if getattr(settings, "LLM_USE_ASYNC", False) and generate_async is not None:
                raw_generated_answer = await generate_async(
                    prompt=full_prompt,
                    chat_history=chat_history,
                    max_output_tokens=4096 if is_exhaustive_list_query(query) else None,
                )
            else:
                raw_generated_answer = self.generation_client.generate_text(
                    prompt=full_prompt,
                    chat_history=chat_history,
                    max_output_tokens=4096 if is_exhaustive_list_query(query) else None,
                )
            RAG_GENERATION_LATENCY.labels(project_id=project_label).observe(time.time() - generation_start)
            answer, needs_clarification = parse_rag_answer(raw_generated_answer)
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
                content={"text": query},
            )
            await chat_message_model.create_chat_message(
                session_id=session_id,
                project_id=project.project_id,
                role=self.generation_client.enums.ASSISTANT.value,
                content={"text": answer},
            )

        return answer, full_prompt, chat_history, needs_clarification

    def _document_text_for_prompt(self, text: str, query: str) -> str:
        chunk_text = text or ""
        if should_focus_document_text(query):
            chunk_text = focus_document_text_for_query(chunk_text, query)
        return chunk_text
