"""Expand stage — fetch adjacent chunk context for high-score items."""

from __future__ import annotations

import logging
import time

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import IChunkReader, IEvidenceExpander
from core.evidence_orchestrator.models import CollectedItem

logger = logging.getLogger(__name__)


class LineageExpander(IEvidenceExpander):
    async def expand(
        self,
        items: list[CollectedItem],
        chunk_reader: IChunkReader,
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]:
        started = time.perf_counter()
        if not items:
            return []

        if not config.expansion_enabled:
            logger.info(
                "stage=expand input_count=%d output_count=%d expanded_count=0 "
                "fetch_failures=0 expansion_enabled=false latency_ms=%.2f",
                len(items),
                len(items),
                (time.perf_counter() - started) * 1000.0,
            )
            return items

        expanded_count = 0
        fetch_failures = 0
        result: list[CollectedItem] = []

        for item in items:
            if item.candidate.score < config.expansion_score_threshold:
                result.append(item)
                continue

            try:
                updated, did_expand, failures = await _expand_item(
                    item, chunk_reader, config
                )
                result.append(updated)
                if did_expand:
                    expanded_count += 1
                fetch_failures += failures
            except Exception as exc:  # noqa: BLE001
                fetch_failures += 1
                logger.error(
                    "expand_item_failed chunk_id=%s error=%s",
                    item.candidate.chunk_id,
                    exc,
                )
                result.append(item)

        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "stage=expand input_count=%d output_count=%d expanded_count=%d "
            "fetch_failures=%d expansion_enabled=true latency_ms=%.2f",
            len(items),
            len(result),
            expanded_count,
            fetch_failures,
            latency_ms,
        )
        return result


async def _expand_item(
    item: CollectedItem,
    chunk_reader: IChunkReader,
    config: EvidenceOrchestratorConfig,
) -> tuple[CollectedItem, bool, int]:
    base_text = item.effective_text
    chunk = await chunk_reader.get_chunk(
        item.candidate.chunk_id,
        item.candidate.document_id,
    )
    if chunk is None:
        logger.warning(
            "expand_chunk_not_found chunk_id=%s document_id=%s",
            item.candidate.chunk_id,
            item.candidate.document_id,
        )
        return item, False, 1

    parts: list[str] = []
    failures = 0
    relationships = chunk.relationships
    short_text = len(base_text) < config.expansion_min_chars

    if short_text and relationships.parent_chunk_id:
        parent = await _safe_fetch(
            chunk_reader,
            relationships.parent_chunk_id,
            item.candidate.document_id,
            item.candidate.chunk_id,
            label="parent",
        )
        if parent is None:
            failures += 1
        else:
            parts.append(parent)

    if item.candidate.score >= config.expansion_score_threshold:
        if relationships.previous_chunk_id:
            prev = await _safe_fetch(
                chunk_reader,
                relationships.previous_chunk_id,
                item.candidate.document_id,
                item.candidate.chunk_id,
                label="previous",
            )
            if prev is None:
                failures += 1
            else:
                parts.insert(0, prev)

        next_parts: list[str] = []
        if relationships.next_chunk_id:
            nxt = await _safe_fetch(
                chunk_reader,
                relationships.next_chunk_id,
                item.candidate.document_id,
                item.candidate.chunk_id,
                label="next",
            )
            if nxt is None:
                failures += 1
            else:
                next_parts.append(nxt)

        merged = "\n".join([p for p in parts if p] + [base_text] + next_parts)
        if merged != base_text:
            return item.model_copy(update={"text": merged, "expanded": True}), True, failures

    if parts:
        merged = "\n".join(parts + [base_text])
        return item.model_copy(update={"text": merged, "expanded": True}), True, failures

    return item, False, failures


async def _safe_fetch(
    chunk_reader: IChunkReader,
    chunk_id: str,
    document_id: str,
    source_chunk_id: str,
    *,
    label: str,
) -> str | None:
    try:
        chunk = await chunk_reader.get_chunk(chunk_id, document_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "expand_fetch_error source_chunk_id=%s %s_chunk_id=%s error=%s",
            source_chunk_id,
            label,
            chunk_id,
            exc,
        )
        return None
    if chunk is None:
        logger.warning(
            "expand_adjacent_not_found source_chunk_id=%s %s_chunk_id=%s",
            source_chunk_id,
            label,
            chunk_id,
        )
        return None
    return chunk.text
