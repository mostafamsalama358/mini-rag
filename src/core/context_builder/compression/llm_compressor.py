"""Optional LLM-based context compressor."""

from __future__ import annotations

import logging

from core.context_builder.interfaces import IContextCompressor
from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import EvidenceItem

logger = logging.getLogger(__name__)

_LLM_FACTORY_AVAILABLE = False
try:
    from stores.llm.LLMProviderFactory import LLMProviderFactory

    _LLM_FACTORY_AVAILABLE = True
except ImportError:
    LLMProviderFactory = None  # type: ignore[misc, assignment]


class LLMContextCompressor(IContextCompressor):
    """Summarize evidence text via LLMProviderFactory when available."""

    def __init__(self, *, llm_factory: object | None = None) -> None:
        if not _LLM_FACTORY_AVAILABLE and llm_factory is None:
            raise ImportError(
                "LLMContextCompressor requires LLMProviderFactory; "
                "use compression_strategy='heuristic' instead."
            )
        self._llm_factory = llm_factory

    async def compress(
        self,
        item: EvidenceItem,
        target_tokens: int,
        token_counter: ITokenCounter,
    ) -> tuple[str, int]:
        if target_tokens <= 0:
            return "", 0

        text = item.text or ""
        if not text.strip():
            return "", 0

        try:
            if self._llm_factory is not None and hasattr(self._llm_factory, "create"):
                client = self._llm_factory.create()
                prompt = (
                    f"Summarize the following text in at most {target_tokens} tokens:\n\n"
                    f"{text}"
                )
                response = await client.agenerate(prompt)
                summary = str(getattr(response, "text", response) or "").strip()
                if summary:
                    return summary, token_counter.count_tokens(summary)
        except Exception as exc:
            logger.warning("LLM compression failed for %s: %s", item.item_id, exc)

        char_limit = max(1, target_tokens * 4)
        truncated = text[:char_limit].strip() or text[:1]
        return truncated, token_counter.count_tokens(truncated)
