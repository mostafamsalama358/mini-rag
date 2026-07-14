"""Tiktoken-based precise token counter (optional dependency)."""

from __future__ import annotations

from core.evidence_orchestrator.interfaces import ITokenCounter


class TiktokenTokenCounter(ITokenCounter):
    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        try:
            import tiktoken
        except ImportError as exc:
            raise ImportError(
                "tiktoken is not installed; install tiktoken or use "
                "token_counter='character' in evidence_orchestrator.yaml"
            ) from exc
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoding.encode(text))
