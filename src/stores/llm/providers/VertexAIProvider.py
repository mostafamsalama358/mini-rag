from ..LLMInterface import LLMInterface
from ..LLMEnums import VertexAIEnums, DocumentTypeEnum
from ..errors import VertexGenerationError
from helpers.config import get_settings
import logging
import time
from typing import Any, List, Union

import vertexai
from google.api_core.exceptions import InvalidArgument, ResourceExhausted
from vertexai.generative_models import Content, GenerativeModel, Part
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel


class VertexAIProvider(LLMInterface):

    def __init__(
        self,
        project_id: str,
        location: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1024,
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

    def _build_embedding_input_batches(
        self,
        text: list[str],
        *,
        task_type: str,
    ) -> list[list[TextEmbeddingInput]]:
        settings = get_settings()
        max_batch_size = max(1, int(getattr(settings, "EMBEDDING_BATCH_SIZE", 32)))
        max_batch_characters = max(
            1,
            int(getattr(settings, "VERTEX_EMBEDDING_MAX_BATCH_CHARACTERS", 12000)),
        )

        batches: list[list[TextEmbeddingInput]] = []
        current_batch: list[TextEmbeddingInput] = []
        current_chars = 0

        for item in text:
            processed = self.process_text(item or "")
            input_item = TextEmbeddingInput(text=processed, task_type=task_type)
            item_chars = len(processed)

            if current_batch and (
                len(current_batch) >= max_batch_size
                or current_chars + item_chars > max_batch_characters
            ):
                batches.append(current_batch)
                current_batch = []
                current_chars = 0

            current_batch.append(input_item)
            current_chars += item_chars

        if current_batch:
            batches.append(current_batch)

        return batches

    def _get_embeddings_with_retry(
        self,
        inputs: list[TextEmbeddingInput],
        *,
        max_retries: int,
        retry_wait: float,
    ):
        for attempt in range(max_retries + 1):
            try:
                return self.embedding_model.get_embeddings(inputs)
            except ResourceExhausted:
                if attempt >= max_retries:
                    self.logger.error(
                        "Vertex AI embedding quota exhausted after %s retries; "
                        "returning None (sparse-only / degraded retrieval)",
                        max_retries,
                    )
                    return None
                self.logger.warning(
                    "Vertex AI embedding quota exceeded (attempt %s/%s), "
                    "retrying in %ss",
                    attempt + 1,
                    max_retries,
                    retry_wait,
                )
                time.sleep(retry_wait)
            except InvalidArgument as exc:
                self.logger.error(
                    "Vertex AI embedding request rejected for batch_size=%s chars=%s: %s",
                    len(inputs),
                    sum(len(getattr(item, "text", "") or "") for item in inputs),
                    exc,
                )
                raise

    def _prompt_text(self, message: dict) -> str:
        return message.get("content") or message.get("text") or ""

    def _to_gemini_role(self, role: str) -> str:
        if role in (VertexAIEnums.ASSISTANT.value, "assistant", "model"):
            return "model"
        return "user"

    def _build_generation_config(
        self,
        *,
        max_output_tokens: int,
        temperature: float,
        response_mime_type: str | None = None,
        response_schema: dict | None = None,
    ):
        config_kwargs: dict[str, Any] = {
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
        }
        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type
        if response_schema:
            config_kwargs["response_schema"] = response_schema

        try:
            from vertexai.generative_models import GenerationConfig

            return GenerationConfig(**config_kwargs)
        except Exception as exc:
            self.logger.warning(
                "Vertex GenerationConfig build failed; using dict fallback: %r",
                exc,
            )
            return config_kwargs

    @staticmethod
    def _serialize_safety_ratings(ratings) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for rating in ratings or []:
            serialized.append(
                {
                    "category": str(getattr(rating, "category", None)),
                    "probability": str(getattr(rating, "probability", None)),
                    "blocked": getattr(rating, "blocked", None),
                    "severity": str(getattr(rating, "severity", None)),
                }
            )
        return serialized

    def _diagnose_vertex_response(
        self,
        response,
        *,
        text_access_error: BaseException | None = None,
    ) -> dict[str, Any]:
        diagnostics: dict[str, Any] = {}
        if text_access_error is not None:
            diagnostics["text_access_error"] = repr(text_access_error)

        if response is None:
            diagnostics["status"] = "no_response"
            return diagnostics

        try:
            diagnostics["text"] = response.text
        except Exception as exc:
            diagnostics["text"] = None
            diagnostics["text_access_error"] = repr(exc)

        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is not None:
            diagnostics["prompt_feedback"] = {
                "block_reason": str(getattr(prompt_feedback, "block_reason", None)),
                "block_reason_message": getattr(prompt_feedback, "block_reason_message", None),
                "safety_ratings": self._serialize_safety_ratings(
                    getattr(prompt_feedback, "safety_ratings", None)
                ),
            }

        candidates = getattr(response, "candidates", None) or []
        diagnostics["candidates_count"] = len(candidates)
        candidate_details: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates[:3]):
            entry: dict[str, Any] = {
                "index": index,
                "finish_reason": str(getattr(candidate, "finish_reason", None)),
                "safety_ratings": self._serialize_safety_ratings(
                    getattr(candidate, "safety_ratings", None)
                ),
            }
            content = getattr(candidate, "content", None)
            if content is not None:
                parts = getattr(content, "parts", None) or []
                entry["parts_count"] = len(parts)
                part_texts: list[str | None] = []
                for part in parts:
                    part_texts.append(getattr(part, "text", None))
                entry["part_texts"] = part_texts
            candidate_details.append(entry)
        diagnostics["candidates"] = candidate_details

        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            diagnostics["usage_metadata"] = {
                "prompt_token_count": getattr(usage, "prompt_token_count", None),
                "candidates_token_count": getattr(usage, "candidates_token_count", None),
                "total_token_count": getattr(usage, "total_token_count", None),
            }

        return diagnostics

    def _infer_failure_category(self, diagnostics: dict[str, Any]) -> str:
        prompt_feedback = diagnostics.get("prompt_feedback") or {}
        block_reason = prompt_feedback.get("block_reason")
        if block_reason and str(block_reason) not in ("None", "BLOCK_REASON_UNSPECIFIED", ""):
            return "vertex_blocked_response"

        for candidate in diagnostics.get("candidates") or []:
            finish_reason = str(candidate.get("finish_reason") or "").upper()
            if "SAFETY" in finish_reason:
                return "vertex_safety_block"
            if "MAX" in finish_reason and "TOKEN" in finish_reason:
                return "vertex_truncated_generation"
            if finish_reason and finish_reason not in (
                "STOP",
                "FINISH_REASON_UNSPECIFIED",
                "1",
                "NONE",
            ):
                return "vertex_finish_reason"

        if diagnostics.get("status") == "no_response":
            return "vertex_no_response"

        text = diagnostics.get("text")
        if text is None or str(text).strip() == "":
            return "vertex_empty_text"

        return "vertex_empty_text"

    def _extract_response_text(self, response) -> str:
        if response is None:
            diagnostics = self._diagnose_vertex_response(None)
            self.logger.error(
                "Vertex AI returned no response object; diagnostics=%r",
                diagnostics,
            )
            raise VertexGenerationError(
                "vertex_no_response",
                "Vertex AI returned no response object",
                diagnostics=diagnostics,
            )

        try:
            text = response.text
        except Exception as exc:
            diagnostics = self._diagnose_vertex_response(
                response,
                text_access_error=exc,
            )
            category = self._infer_failure_category(diagnostics)
            self.logger.warning(
                "Vertex AI response.text unavailable category=%s diagnostics=%r",
                category,
                diagnostics,
            )
            raise VertexGenerationError(
                category,
                f"Vertex AI response.text unavailable ({category})",
                diagnostics=diagnostics,
                cause=exc,
            ) from exc

        if not text or not str(text).strip():
            diagnostics = self._diagnose_vertex_response(response)
            category = self._infer_failure_category(diagnostics)
            self.logger.warning(
                "Vertex AI empty text category=%s diagnostics=%r",
                category,
                diagnostics,
            )
            raise VertexGenerationError(
                category,
                f"Vertex AI returned empty text ({category})",
                diagnostics=diagnostics,
            )

        return str(text)

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = None,
        temperature: float = None,
        *,
        response_mime_type: str | None = None,
        response_schema: dict | None = None,
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
                parts=[Part.from_text((prompt or "").strip())],
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

        generation_config = self._build_generation_config(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )

        try:
            response = model.generate_content(
                contents,
                generation_config=generation_config,
            )
        except ResourceExhausted as exc:
            self.logger.warning(
                "Vertex AI generation quota exhausted: %r",
                exc,
                exc_info=True,
            )
            raise VertexGenerationError(
                "vertex_quota",
                "Vertex AI generation quota exhausted",
                cause=exc,
            ) from exc

        return self._extract_response_text(response)

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.embedding_model:
            self.logger.error("Embedding model for Vertex AI was not set")
            return None

        if isinstance(text, str):
            text = [text]

        task_type = "RETRIEVAL_DOCUMENT"
        if document_type == DocumentTypeEnum.QUERY.value:
            task_type = "RETRIEVAL_QUERY"

        settings = get_settings()
        max_retries = settings.VERTEX_EMBEDDING_RATE_LIMIT_RETRIES
        retry_wait = settings.VERTEX_EMBEDDING_RATE_LIMIT_RETRY_WAIT_SECONDS
        all_embeddings = []

        for batch in self._build_embedding_input_batches(text, task_type=task_type):
            embeddings = self._get_embeddings_with_retry(
                batch,
                max_retries=max_retries,
                retry_wait=retry_wait,
            )
            if not embeddings:
                self.logger.error("Error while embedding text with Vertex AI")
                return None
            all_embeddings.extend(embeddings)

        if not all_embeddings:
            self.logger.error("Error while embedding text with Vertex AI")
            return None

        return [embedding.values for embedding in all_embeddings]

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt,
        }
