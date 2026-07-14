"""Section-path document-structure stitcher."""

from __future__ import annotations

from core.context_builder.interfaces import IContextStitcher
from core.context_builder.models import ContextBlock
from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import EvidenceItem


class SectionPathStitcher(IContextStitcher):
    async def stitch(
        self,
        items: list[tuple[EvidenceItem, str, bool]],
        token_counter: ITokenCounter,
    ) -> list[ContextBlock]:
        sorted_items = sorted(items, key=_sort_key)
        blocks: list[ContextBlock] = []
        for item, text, compressed in sorted_items:
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


def _sort_key(entry: tuple[EvidenceItem, str, bool]) -> tuple:
    item, _, _ = entry
    doc_id = item.doc_id or ""
    doc_id_sort = ("\xff", doc_id) if not doc_id else ("", doc_id)
    section_path_list = item.section_path if item.section_path else ["\xff"]
    return (doc_id_sort, section_path_list, -item.relevance_score)
