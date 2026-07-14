"""Context Builder async pipeline orchestration."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from core.context_builder.config import ContextBuilderConfig
from core.context_builder.dedup.text_similarity_dedup import FinalPassDeduplicator
from core.context_builder.errors import (
    CitationIntegrityError,
    EmptyBudgetError,
    EvidencePackVersionError,
)
from core.context_builder.interfaces import (
    IConflictDetector,
    IContextCompressor,
    IContextStitcher,
    ITokenBudgetAllocator,
)
from core.context_builder.models import (
    ConflictGroup,
    Context,
    ContextBlock,
    ContextMetadata,
    compute_context_id,
    utc_now_iso,
)
from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import EvidenceItem, EvidencePack

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectedItem:
    item: EvidenceItem
    text: str
    compressed: bool


class ContextBuilderPipeline:
    def __init__(
        self,
        *,
        budget_allocator: ITokenBudgetAllocator,
        compressor: IContextCompressor,
        conflict_detector: IConflictDetector,
        stitcher: IContextStitcher,
        token_counter: ITokenCounter,
        deduplicator: FinalPassDeduplicator | None = None,
    ) -> None:
        self._budget_allocator = budget_allocator
        self._compressor = compressor
        self._conflict_detector = conflict_detector
        self._stitcher = stitcher
        self._token_counter = token_counter
        self._deduplicator = deduplicator or FinalPassDeduplicator()

    async def build(
        self,
        pack: EvidencePack,
        config: ContextBuilderConfig,
    ) -> Context:
        start = time.perf_counter()
        _validate_pack_version(pack, config)

        budget = self._budget_allocator.allocate(config)
        logger.info(
            "context_builder_start pack_id=%s plan_id=%s items_in=%d token_budget=%d",
            pack.pack_id,
            pack.plan_id,
            len(pack.items),
            budget,
        )

        if budget <= 0:
            raise EmptyBudgetError(
                f"available budget is {budget} after reservations "
                f"(window={config.total_context_window})"
            )

        try:
            return await asyncio.wait_for(
                self._build_inner(pack, config, budget, start),
                timeout=config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.warning(
                "context_builder_timeout pack_id=%s plan_id=%s elapsed_ms=%.2f",
                pack.pack_id,
                pack.plan_id,
                elapsed_ms,
            )
            return _empty_context(
                pack=pack,
                budget_total=budget,
                items_dropped=len(pack.items),
                timeout=True,
            )

    async def _build_inner(
        self,
        pack: EvidencePack,
        config: ContextBuilderConfig,
        budget: int,
        start: float,
    ) -> Context:
        if not pack.items:
            return _empty_context(
                pack=pack,
                budget_total=budget,
                items_dropped=0,
                timeout=False,
            )

        selected, selection_dropped, items_compressed = await _select_under_budget(
            pack.items,
            budget=budget,
            config=config,
            compressor=self._compressor,
            token_counter=self._token_counter,
        )

        selected_by_id = {entry.item.item_id: entry for entry in selected}
        deduped, dedup_removed = self._deduplicator.deduplicate(
            [entry.item for entry in selected],
            config,
        )
        selected_tuples = [
            (
                item,
                selected_by_id[item.item_id].text,
                selected_by_id[item.item_id].compressed,
            )
            for item in deduped
            if item.item_id in selected_by_id
        ]

        conflicts = await self._conflict_detector.detect(deduped, config)
        blocks = await self._stitcher.stitch(selected_tuples, self._token_counter)

        included_ids = {block.item_id for block in blocks}
        conflicts = _apply_conflict_resolutions(conflicts, included_ids)

        citation_map = {
            block.item_id: next(
                item.citation for item in deduped if item.item_id == block.item_id
            )
            for block in blocks
        }

        items_dropped = selection_dropped + dedup_removed
        token_count = sum(block.token_count for block in blocks)
        items_compressed_count = sum(1 for block in blocks if block.compressed)

        _assert_citation_integrity(blocks, citation_map)

        created_at = utc_now_iso()
        context = Context(
            context_id=compute_context_id(pack.pack_id, created_at),
            pack_id=pack.pack_id,
            plan_id=pack.plan_id,
            ordered_blocks=blocks,
            citation_map=citation_map,
            token_count=token_count,
            conflicts=conflicts,
            metadata=ContextMetadata(
                items_included=len(blocks),
                items_dropped=items_dropped,
                items_compressed=items_compressed_count,
                conflicts_detected=len(conflicts) > 0,
                budget_total=budget,
                budget_used=token_count,
                timeout=False,
            ),
            created_at=created_at,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if selection_dropped > 0:
            logger.warning(
                "CONTEXT_HARD_DROP pack_id=%s plan_id=%s items_dropped=%d",
                pack.pack_id,
                pack.plan_id,
                selection_dropped,
            )
        logger.info(
            "context_builder_complete pack_id=%s plan_id=%s items_selected=%d "
            "items_compressed=%d items_dropped=%d final_dedup_removed=%d "
            "conflicts_detected=%d elapsed_ms=%.2f",
            pack.pack_id,
            pack.plan_id,
            len(blocks),
            items_compressed_count,
            items_dropped,
            dedup_removed,
            len(conflicts),
            elapsed_ms,
        )
        return context


async def _select_under_budget(
    items: list[EvidenceItem],
    *,
    budget: int,
    config: ContextBuilderConfig,
    compressor: IContextCompressor,
    token_counter: ITokenCounter,
) -> tuple[list[SelectedItem], int, int]:
    selected: list[SelectedItem] = []
    budget_used = 0
    items_compressed = 0

    for item in items:
        text = item.text
        token_count = token_counter.count_tokens(text)
        compressed = False

        if budget_used + token_count <= budget:
            selected.append(SelectedItem(item=item, text=text, compressed=False))
            budget_used += token_count
            continue

        if (
            config.compression_enabled
            and item.compressibility_score > config.compressibility_threshold
        ):
            remaining = budget - budget_used
            if remaining > 0:
                compressed_text, compressed_tokens = await compressor.compress(
                    item,
                    remaining,
                    token_counter,
                )
                if compressed_text and compressed_tokens > 0:
                    if budget_used + compressed_tokens <= budget:
                        selected.append(
                            SelectedItem(
                                item=item,
                                text=compressed_text,
                                compressed=True,
                            )
                        )
                        budget_used += compressed_tokens
                        items_compressed += 1
                        continue

    items_dropped = len(items) - len(selected)
    return selected, items_dropped, items_compressed


def _validate_pack_version(pack: EvidencePack, config: ContextBuilderConfig) -> None:
    expected_major = config.evidence_pack_schema_version.split(".", maxsplit=1)[0]
    actual_major = pack.schema_version.split(".", maxsplit=1)[0]
    if expected_major != actual_major:
        raise EvidencePackVersionError(
            f"EvidencePack schema major version {actual_major!r} "
            f"does not match expected {expected_major!r}"
        )


def _apply_conflict_resolutions(
    conflicts: list[ConflictGroup],
    included_ids: set[str],
) -> list[ConflictGroup]:
    resolved: list[ConflictGroup] = []
    for group in conflicts:
        resolution = group.resolution
        if any(item_id not in included_ids for item_id in group.item_ids):
            if any(item_id in included_ids for item_id in group.item_ids):
                resolution = "budget_drop"
        resolved.append(
            ConflictGroup(
                entity_tag=group.entity_tag,
                attribute=group.attribute,
                item_ids=list(group.item_ids),
                resolution=resolution,
            )
        )
    return resolved


def _assert_citation_integrity(
    blocks: list[ContextBlock],
    citation_map: dict,
) -> None:
    block_ids = {block.item_id for block in blocks}
    citation_ids = set(citation_map.keys())
    if block_ids != citation_ids:
        missing = block_ids - citation_ids
        extra = citation_ids - block_ids
        raise CitationIntegrityError(
            f"citation map mismatch: missing={sorted(missing)} extra={sorted(extra)}"
        )


def _empty_context(
    *,
    pack: EvidencePack,
    budget_total: int,
    items_dropped: int,
    timeout: bool,
) -> Context:
    created_at = utc_now_iso()
    return Context(
        context_id=compute_context_id(pack.pack_id, created_at),
        pack_id=pack.pack_id,
        plan_id=pack.plan_id,
        ordered_blocks=[],
        citation_map={},
        token_count=0,
        conflicts=[],
        metadata=ContextMetadata(
            items_included=0,
            items_dropped=items_dropped,
            items_compressed=0,
            conflicts_detected=False,
            budget_total=budget_total,
            budget_used=0,
            timeout=timeout,
        ),
        created_at=created_at,
    )
