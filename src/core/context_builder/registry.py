"""Registry wiring concrete Context Builder stage implementations."""

from __future__ import annotations

from core.context_builder.budget.default_allocator import DefaultTokenBudgetAllocator
from core.context_builder.compression.heuristic_compressor import (
    HeuristicTruncationCompressor,
)
from core.context_builder.compression.llm_compressor import LLMContextCompressor
from core.context_builder.conflict.entity_tag_detector import EntityTagConflictDetector
from core.context_builder.config import ContextBuilderConfig
from core.context_builder.interfaces import (
    IConflictDetector,
    IContextCompressor,
    IContextStitcher,
    ITokenBudgetAllocator,
)
from core.context_builder.models import ContextBlock
from core.context_builder.pipeline import ContextBuilderPipeline
from core.context_builder.stitching.section_path_stitcher import SectionPathStitcher
from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import EvidenceItem
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from core.evidence_orchestrator.token_counting.tiktoken_counter import (
    TiktokenTokenCounter,
)


class NoOpConflictDetector(IConflictDetector):
    async def detect(self, items, config):
        _ = items, config
        return []


class PassthroughStitcher(IContextStitcher):
    async def stitch(
        self,
        items: list[tuple[EvidenceItem, str, bool]],
        token_counter: ITokenCounter,
    ) -> list[ContextBlock]:
        blocks: list[ContextBlock] = []
        for item, text, compressed in items:
            section_path = "/".join(item.section_path) if item.section_path else None
            blocks.append(
                ContextBlock(
                    item_id=item.item_id,
                    document_id=item.doc_id,
                    section_path=section_path,
                    text=text,
                    token_count=token_counter.count_tokens(text),
                    compressed=compressed,
                )
            )
        return blocks


class ContextBuilderRegistry:
    @staticmethod
    def build(config: ContextBuilderConfig) -> ContextBuilderPipeline:
        token_counter = _resolve_token_counter(config.token_counter)
        compressor = _resolve_compressor(config.compression_strategy)

        return ContextBuilderPipeline(
            budget_allocator=DefaultTokenBudgetAllocator(),
            compressor=compressor,
            conflict_detector=EntityTagConflictDetector(),
            stitcher=SectionPathStitcher(),
            token_counter=token_counter,
        )


def _resolve_token_counter(name: str) -> ITokenCounter:
    if name == "character":
        return CharacterApproximationTokenCounter()
    if name == "tiktoken":
        return TiktokenTokenCounter()
    raise ValueError(f"unknown token_counter {name!r}; expected 'character' or 'tiktoken'")


def _resolve_compressor(strategy: str) -> IContextCompressor:
    if strategy == "heuristic":
        return HeuristicTruncationCompressor()
    if strategy == "llm":
        return LLMContextCompressor()
    raise ValueError(
        f"unknown compression_strategy {strategy!r}; expected 'heuristic' or 'llm'"
    )
