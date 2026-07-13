
from .LLMEnums import LLMEnums


class LLMProviderFactory:
    def __init__(self, config: dict):
        self.config = config

    def create(self, provider: str):
        if provider == LLMEnums.OPENAI.value:
            from .providers.OpenAIProvider import OpenAIProvider

            return OpenAIProvider(
                api_key = self.config.OPENAI_API_KEY,
                api_url = self.config.OPENAI_API_URL,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.COHERE.value:
            from .providers.CoHereProvider import CoHereProvider

            return CoHereProvider(
                api_key = self.config.COHERE_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.VERTEX.value:
            from .providers.VertexAIProvider import VertexAIProvider

            return VertexAIProvider(
                project_id=self.config.VERTEX_PROJECT_ID,
                location=self.config.VERTEX_LOCATION,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE,
            )

        if provider == LLMEnums.DEEPSEEK.value:
            from .providers.OpenAIProvider import OpenAIProvider

            return OpenAIProvider(
                api_key=self.config.DEEPSEEK_API_KEY,
                api_url=self.config.DEEPSEEK_API_URL or "https://api.deepseek.com",
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.BGE.value:
            from .providers.BGEProvider import BGEProvider
            return BGEProvider(
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS
            )

        return None
