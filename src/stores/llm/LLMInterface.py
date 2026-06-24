from abc import ABC, abstractmethod

class LLMInterface(ABC):

    @abstractmethod
    def set_generation_model(self, model_id: str):
        pass

    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int):
        pass

    @abstractmethod
    def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int=None,
                            temperature: float = None):
        pass

    @abstractmethod
    def embed_text(self, text: str, document_type: str = None):
        pass

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str):
        pass

    # ------------------------------------------------------------------
    # Optional async surface. Default implementations delegate to the sync
    # methods so providers that have no native async client still work, but
    # run inside a worker thread to avoid blocking the event loop.
    # Providers with a real async client (e.g. AsyncOpenAI) override these.
    # ------------------------------------------------------------------
    async def generate_text_async(self, prompt: str, chat_history: list = None,
                                  max_output_tokens: int = None,
                                  temperature: float = None):
        import asyncio
        return await asyncio.to_thread(
            self.generate_text, prompt, chat_history or [], max_output_tokens, temperature
        )

    async def embed_text_async(self, text, document_type: str = None):
        import asyncio
        return await asyncio.to_thread(self.embed_text, text, document_type)
