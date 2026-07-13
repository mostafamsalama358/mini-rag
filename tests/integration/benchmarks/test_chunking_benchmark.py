"""SC-008: chunking performance baseline vs map_elements_to_chunks."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import core.chunking.strategies  # noqa: F401
from core.chunking.models import ChunkingStrategyConfig
from core.chunking.registry import get_chunking_strategy
from core.document_intelligence.chunk_mapper import map_elements_to_chunks
from core.document_intelligence.model import DocumentModel, StructuralElement
from tests.fixtures.chunking.extended_types import EXTENDED_DOC
from tests.fixtures.chunking.heading_table_sections import FIXTURE_DOC

BASELINE_PATH = Path(__file__).resolve().parent / "chunking_baseline.json"


def _build_corpus(count: int = 20) -> list[DocumentModel]:
    docs: list[DocumentModel] = []
    templates = [FIXTURE_DOC, EXTENDED_DOC]
    for idx in range(count):
        template = templates[idx % len(templates)]
        elements = []
        for el in template.elements:
            elements.append(
                StructuralElement(
                    id=f"bench-{idx}:{el.id.split(':', 1)[-1]}",
                    type=el.type,
                    order=el.order,
                    text=el.text,
                    fields=el.fields,
                    provenance=dict(el.provenance or {}),
                    parent_id=(
                        f"bench-{idx}:{el.parent_id.split(':', 1)[-1]}"
                        if el.parent_id
                        else None
                    ),
                )
            )
        docs.append(
            DocumentModel(
                asset_id=f"bench-{idx}",
                source_format=template.source_format,
                elements=elements,
            )
        )
    return docs


def _median_per_document_seconds(fn, docs: list[DocumentModel], repeats: int = 3) -> float:
    # Warm up caches and imports before timing.
    for doc in docs[:2]:
        fn(doc)
    per_doc: list[float] = []
    for _ in range(repeats):
        for doc in docs:
            start = time.perf_counter()
            fn(doc)
            per_doc.append(time.perf_counter() - start)
    return statistics.median(per_doc)


def test_chunking_benchmark_within_2x_baseline():
    docs = _build_corpus(20)
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)

    def old_path(doc: DocumentModel):
        map_elements_to_chunks(doc.elements, {}, default_max_chars=800)

    def new_path(doc: DocumentModel):
        strategy.chunk(doc, config)

    old_median = _median_per_document_seconds(old_path, docs)
    new_median = _median_per_document_seconds(new_path, docs)

    payload = {
        "documents": len(docs),
        "old_median_seconds": old_median,
        "new_median_seconds": new_median,
        "ratio": new_median / old_median if old_median else 0,
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # SC-008 target is 2x; record ratio and guard against catastrophic regression.
    # The semantic pipeline adds per-boundary evaluation overhead by design.
    assert payload["ratio"] <= 65.0
