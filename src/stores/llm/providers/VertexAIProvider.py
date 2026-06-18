from ..LLMInterface import LLMInterface
from ..LLMEnums import VertexAIEnums, DocumentTypeEnum
from helpers.config import get_settings
import logging
import time
from typing import List, Union

import vertexai
from google.api_core.exceptions import ResourceExhausted
from vertexai.generative_models import Content, GenerativeModel, Part
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel


class VertexAIProvider(LLMInterface):

    def __init__(
        self,
        project_id: str,
        location: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
    ):
        self.project_id = project_id
        self.location = location
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        vertexai.init(project=self.project_id, location=self.location)

        self.generation_model = None
        self.embedding_model = None

        self.enums = VertexAIEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id
        self.generation_model = GenerativeModel(model_id)

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.embedding_model = TextEmbeddingModel.from_pretrained(model_id)

    def process_text(self, text: str) -> str:
        return text[: self.default_input_max_characters].strip()

    def _prompt_text(self, message: dict) -> str:
        return message.get("content") or message.get("text") or ""

    def _to_gemini_role(self, role: str) -> str:
        if role in (VertexAIEnums.ASSISTANT.value, "assistant", "model"):
            return "model"
        return "user"

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        if not self.generation_model:
            self.logger.error("Generation model for Vertex AI was not set")
            return None

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens
            else self.default_generation_max_output_tokens
        )
        temperature = (
            temperature if temperature else self.default_generation_temperature
        )

        system_instruction = None
        contents: List[Content] = []

        for message in chat_history:
            role = message.get("role", VertexAIEnums.USER.value)
            text = self.process_text(self._prompt_text(message))

            if role == VertexAIEnums.SYSTEM.value:
                system_instruction = text
                continue

            contents.append(
                Content(
                    role=self._to_gemini_role(role),
                    parts=[Part.from_text(text)],
                )
            )

        contents.append(
            Content(
                role="user",
                parts=[Part.from_text(self.process_text(prompt))],
            )
        )

        model = (
            GenerativeModel(
                self.generation_model_id,
                system_instruction=system_instruction,
            )
            if system_instruction
            else self.generation_model
        )

        response = model.generate_content(
            contents,
            generation_config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
            },
        )

        if not response or not response.text:
            self.logger.error("Error while generating text with Vertex AI")
            return None

        return response.text

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.embedding_model:
            self.logger.error("Embedding model for Vertex AI was not set")
            return None

        if isinstance(text, str):
            text = [text]

        task_type = "RETRIEVAL_DOCUMENT"
        if document_type == DocumentTypeEnum.QUERY.value:
            task_type = "RETRIEVAL_QUERY"

        inputs = [
            TextEmbeddingInput(
                text=self.process_text(item),
                task_type=task_type,
            )
            for item in text
        ]

        settings = get_settings()
        max_retries = settings.VERTEX_EMBEDDING_RATE_LIMIT_RETRIES
        retry_wait = settings.VERTEX_EMBEDDING_RATE_LIMIT_RETRY_WAIT_SECONDS
        embeddings = None

        for attempt in range(max_retries + 1):
            try:
                embeddings = self.embedding_model.get_embeddings(inputs)
                break
            except ResourceExhausted:
                if attempt >= max_retries:
                    raise
                self.logger.warning(
                    "Vertex AI embedding quota exceeded (attempt %s/%s), "
                    "retrying in %ss",
                    attempt + 1,
                    max_retries,
                    retry_wait,
                )
                time.sleep(retry_wait)

        if not embeddings:
            self.logger.error("Error while embedding text with Vertex AI")
            return None

        return [embedding.values for embedding in embeddings]

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt,
        }
