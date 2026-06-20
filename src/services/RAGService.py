from models.ChatMessageModel import ChatMessageModel
from models.db_schemes import Project
from helpers.config import get_settings
from utils.chunk_metadata import format_source_label
from utils.detect_language import detect_query_language
from utils.rag_history import select_chat_history_messages
from utils.rag_response import parse_rag_answer
from utils.retrieval import (
    focus_document_text_for_query,
    rerank_retrieved_documents,
    should_focus_document_text,
    sort_documents_for_prompt,
)
from utils.structural_split import is_exhaustive_list_query


class RAGService:

    def __init__(self, db_client, nlp_controller, generation_client, template_parser):
        self.db_client = db_client
        self.nlp_controller = nlp_controller
        self.generation_client = generation_client
        self.template_parser = template_parser

    async def answer_question(
        self,
        *,
        project: Project,
        query: str,
        limit: int = 12,
        session_id: str | None = None,
    ):
        answer, full_prompt, chat_history = None, None, None
        needs_clarification = False

        retrieved_documents = await self.nlp_controller.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )

        if not retrieved_documents:
            return answer, full_prompt, chat_history, needs_clarification

        retrieved_documents = await self.nlp_controller.enrich_retrieved_documents(
            project=project,
            documents=retrieved_documents,
            db_client=self.db_client,
            query=query,
        )
        settings = get_settings()
        rrf_k = max(1, int(getattr(settings, "RAG_RRF_K", 60)))
        retrieved_documents = rerank_retrieved_documents(retrieved_documents, query, rrf_k=rrf_k)
        retrieved_documents = sort_documents_for_prompt(retrieved_documents, query)

        previous_lang = self.template_parser.language
        query_lang = detect_query_language(
            query,
            default=getattr(self.template_parser, "default_language", "en"),
        )
        self.template_parser.set_language(query_lang)
        template_lang = query_lang

        try:
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

            raw_answer = self.generation_client.generate_text(
                prompt=full_prompt,
                chat_history=chat_history,
                max_output_tokens=4096 if is_exhaustive_list_query(query) else None,
            )
            answer, needs_clarification = parse_rag_answer(raw_answer)
        finally:
            self.template_parser.set_language(previous_lang)

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
