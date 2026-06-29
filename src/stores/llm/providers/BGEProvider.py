from ..LLMInterface import LLMInterface
import logging
from typing import List, Union

from utils.bge_model_cache import get_bge_embedding_model, run_bge_embedding_inference

class BGEProvider(LLMInterface):

    def __init__(self, default_input_max_characters: int=1000):
        self.default_input_max_characters = default_input_max_characters
        self.embedding_model_id = None
        self.embedding_size = None
        self.model = None
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        pass # Not supported for BGE embedding provider

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        try:
            self.model, load_elapsed = get_bge_embedding_model(
                self.embedding_model_id,
                use_fp16=True,
            )
            if load_elapsed > 0:
                self.logger.info(
                    "BGE embedding model ready: %s (loaded in %.2fs)",
                    self.embedding_model_id,
                    load_elapsed,
                )
            else:
                self.logger.info(
                    "BGE embedding model ready: %s (reused cached instance)",
                    self.embedding_model_id,
                )
        except ImportError:
            self.logger.error("FlagEmbedding package not found. Please install FlagEmbedding.")
        except Exception as e:
            self.logger.error(f"Failed to load BGE model {self.embedding_model_id}: {e}")

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int=None,
                            temperature: float = None):
        self.logger.error("BGEProvider does not support text generation")
        return None

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.model:
            self.logger.error("BGE model was not initialized")
            return None
        
        if isinstance(text, str):
            text = [text]
            
        processed_texts = [self.process_text(t) for t in text]
        
        try:
            def _encode():
                embeddings = self.model.encode(
                    processed_texts,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False,
                )
                dense_vecs = embeddings.get("dense_vecs", [])
                return [vec.tolist() for vec in dense_vecs]

            return run_bge_embedding_inference(_encode)
        except Exception as e:
            self.logger.error(f"Error embedding text with BGE: {e}")
            return None

    def construct_prompt(self, prompt: str, role: str):
        return {}
