"""Heuristic sentence-boundary truncation compressor."""

from __future__ import annotations

import re

from core.context_builder.interfaces import IContextCompressor
from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import EvidenceItem

_SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")


class HeuristicTruncationCompressor(IContextCompressor):
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
            sentences = _SENTENCE_SPLIT.split(text)
            if not sentences:
                sentences = [text]

            selected: list[str] = []
            for sentence in sentences:
                candidate = " ".join(selected + [sentence]).strip()
                if token_counter.count_tokens(candidate) <= target_tokens:
                    selected.append(sentence)
                else:
                    break

            if selected:
                result = " ".join(selected).strip()
                return result, token_counter.count_tokens(result)

            char_limit = max(1, target_tokens * 4)
            truncated = text[:char_limit].strip()
            if not truncated:
                truncated = text[:1]
            return truncated, token_counter.count_tokens(truncated)
        except Exception:
            char_limit = max(1, target_tokens * 4)
            truncated = text[:char_limit].strip() or text[:1]
            return truncated, token_counter.count_tokens(truncated)
