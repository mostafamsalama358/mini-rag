from models.ChatMessageModel import ChatMessageModel
from models.db_schemes import Project
from utils.chunk_metadata import format_source_label


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
        limit: int = 10,
        session_id: str | None = None,
    ):
        answer, full_prompt, chat_history = None, None, None

        retrieved_documents = await self.nlp_controller.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )

        if not retrieved_documents:
            return answer, full_prompt, chat_history

        system_prompt = self.template_parser.get("rag", "system_prompt")
        template_lang = getattr(self.template_parser, "language", "en")

        documents_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                "doc_num": idx + 1,
                "source_label": format_source_label(doc.metadata, lang=template_lang),
                "chunk_text": self.generation_client.process_text(doc.text),
            })
            for idx, doc in enumerate(retrieved_documents)
        ])

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

            for message in prior_messages:
                chat_history.append(
                    self.generation_client.construct_prompt(
                        prompt=message.content.get("text", ""),
                        role=message.role,
                    )
                )

        full_prompt = "\n\n".join([documents_prompts, footer_prompt])

        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )

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

        return answer, full_prompt, chat_history
