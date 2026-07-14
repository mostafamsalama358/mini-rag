"""Resolve item_id citation markers against Context.citation_map."""

from __future__ import annotations

import re

from core.answer_generation.interfaces import ICitationFormatter
from core.answer_generation.models import CitationReference
from core.evidence_orchestrator.models import Citation

_ITEM_ID_PATTERN = re.compile(r"\[(ei_[0-9a-f]{16})\]")


class ItemIdCitationFormatter(ICitationFormatter):
    def format(
        self,
        answer_text: str,
        citation_map: dict[str, Citation],
    ) -> list[CitationReference]:
        if not answer_text:
            return []

        seen: set[str] = set()
        citations: list[CitationReference] = []

        for match in _ITEM_ID_PATTERN.finditer(answer_text):
            item_id = match.group(1)
            if item_id in seen:
                continue
            seen.add(item_id)

            citation = citation_map.get(item_id)
            if citation is None:
                continue

            citations.append(
                CitationReference(
                    citation_id=item_id,
                    document_id=citation.document_id,
                    chunk_id=citation.chunk_id,
                    document_title=citation.document_title,
                    section_title=citation.section_title,
                    page_number=citation.page_number,
                    retrieval_score=citation.retrieval_score,
                )
            )

        return citations
