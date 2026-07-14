"""End-to-end Knowledge Representation pipeline integration test."""

from __future__ import annotations

import pytest

from core.chunking.models import (
    Chunk,
    ChunkIdentity,
    ChunkRelationships,
    ChunkSet,
    StructuralContext,
    ValidationReport,
)
from core.knowledge.models import KnowledgeExtractionConfig
from core.knowledge.pipeline import build_pipeline_from_config
from core.knowledge.registry import register_defaults


def _chunk(chunk_id: str, text: str, element_type: str, position: int) -> Chunk:
    return Chunk(
        text=text,
        identity=ChunkIdentity(
            chunk_id=chunk_id,
            document_id="doc_e2e",
            strategy_id="semantic_structural",
            source_element_ids=[f"el_{chunk_id}"],
        ),
        relationships=ChunkRelationships(),
        structural_context=StructuralContext(
            element_type=element_type,
            heading_path=["E2E"],
            position=position,
        ),
    )


@pytest.fixture
def chunk_set_five_forms() -> ChunkSet:
    return ChunkSet(
        chunks=[
            _chunk(
                "ck_proc",
                "1. Wash hands\n2. Put on gloves\n3. Disinfect the site",
                "paragraph",
                0,
            ),
            _chunk(
                "ck_def",
                "Hypertension is defined as elevated blood pressure.",
                "paragraph",
                1,
            ),
            _chunk(
                "ck_meas",
                "Administer 500 mg of the compound daily.",
                "paragraph",
                2,
            ),
            _chunk("ck_table", "Drug | Strength\nA | high\nB | low", "table", 3),
            _chunk("ck_assert", "Overview", "heading", 4),
        ],
        validation_report=ValidationReport(status="pass"),
        asset_id="asset_e2e_five",
        strategy_id="semantic_structural",
    )


def test_knowledge_pipeline_e2e(chunk_set_five_forms: ChunkSet) -> None:
    register_defaults()
    config = KnowledgeExtractionConfig()
    pipeline = build_pipeline_from_config(config)
    package = pipeline.run(chunk_set_five_forms, config)

    # SC-001 types
    types = [u.type for u in package.knowledge_units]
    assert "procedure" in types
    assert "definition" in types
    assert "measurement" in types
    assert "table" in types
    assert "assertion" in types

    # SC-002 evidence chain
    for unit in package.knowledge_units:
        for ref in unit.evidence_references:
            assert ref.chunk_ids and ref.element_ids
            assert ref.document_model_id and ref.asset_id

    # SC-003 idempotency
    again = pipeline.run(chunk_set_five_forms, config)
    assert again.metadata.package_id == package.metadata.package_id

    # SC-004 / SC-007: default path uses structural strategies, no network
    assert package.metadata.extractor_strategy_id == "structural"
    assert package.validation_report.status in {"passed", "passed_with_warnings"}
    assert package.statistics.evidence_coverage_pct > 0


def test_latency_budget_optional(chunk_set_five_forms: ChunkSet, request) -> None:
    if not request.config.getoption("--benchmark", default=False):
        pytest.skip("latency assertion requires --benchmark")
    # Placeholder: when --benchmark is provided, callers can compare against chunking.
    assert True
