"""Shared fixtures for Knowledge Representation unit tests."""

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


def _chunk(
    *,
    chunk_id: str,
    text: str,
    element_type: str,
    element_ids: list[str] | None = None,
    document_id: str = "doc_test",
    heading_path: list[str] | None = None,
    parent_chunk_id: str | None = None,
    position: int = 0,
) -> Chunk:
    return Chunk(
        text=text,
        identity=ChunkIdentity(
            chunk_id=chunk_id,
            document_id=document_id,
            strategy_id="semantic_structural",
            source_element_ids=element_ids or [f"el_{chunk_id}"],
        ),
        relationships=ChunkRelationships(parent_chunk_id=parent_chunk_id),
        structural_context=StructuralContext(
            element_type=element_type,
            heading_path=heading_path or [],
            position=position,
        ),
    )


@pytest.fixture
def chunk_set_five_forms() -> ChunkSet:
    """Five semantic forms: procedure, definition, measurement, table, assertion."""
    chunks = [
        _chunk(
            chunk_id="ck_proc",
            text="1. Wash hands\n2. Put on gloves\n3. Disinfect the site",
            element_type="paragraph",
            heading_path=["Safety"],
            position=0,
        ),
        _chunk(
            chunk_id="ck_def",
            text="Hypertension is defined as elevated blood pressure.",
            element_type="paragraph",
            heading_path=["Definitions"],
            position=1,
        ),
        _chunk(
            chunk_id="ck_meas",
            text="Administer 500 mg of the compound daily.",
            element_type="paragraph",
            heading_path=["Dosage"],
            position=2,
        ),
        _chunk(
            chunk_id="ck_table",
            text="Drug | Strength\nA | high\nB | low",
            element_type="table",
            heading_path=["Tables"],
            position=3,
        ),
        _chunk(
            chunk_id="ck_assert",
            text="Overview",
            element_type="heading",
            heading_path=["Overview"],
            position=4,
        ),
    ]
    return ChunkSet(
        chunks=chunks,
        validation_report=ValidationReport(status="pass"),
        asset_id="asset_five_forms",
        strategy_id="semantic_structural",
        element_counts_by_type={
            "paragraph": 3,
            "table": 1,
            "heading": 1,
        },
    )


@pytest.fixture
def chunk_set_alias_pair() -> ChunkSet:
    """Two chunks whose surface forms are aliases of the same concept."""
    chunks = [
        _chunk(
            chunk_id="ck_asa",
            text="ASA",
            element_type="paragraph",
            heading_path=["Compounds"],
            position=0,
        ),
        _chunk(
            chunk_id="ck_acetyl",
            text="acetylsalicylic acid",
            element_type="paragraph",
            heading_path=["Compounds"],
            position=1,
        ),
    ]
    return ChunkSet(
        chunks=chunks,
        validation_report=ValidationReport(status="pass"),
        asset_id="asset_alias_pair",
        strategy_id="semantic_structural",
    )


@pytest.fixture
def chunk_set_single_degraded() -> ChunkSet:
    """Single-chunk ChunkSet with degraded (warning) validation status."""
    return ChunkSet(
        chunks=[
            _chunk(
                chunk_id="ck_deg",
                text="Degraded input still yields a knowledge unit.",
                element_type="paragraph",
            )
        ],
        validation_report=ValidationReport(
            status="pass_with_warnings",
            warnings=["oversized_chunk"],
        ),
        asset_id="asset_degraded",
        strategy_id="semantic_structural",
    )


@pytest.fixture
def chunk_set_malformed() -> ChunkSet:
    """ChunkSet used to inject validation violations via model_construct."""
    return ChunkSet(
        chunks=[
            _chunk(
                chunk_id="ck_mal",
                text="Malformed package fixture source.",
                element_type="paragraph",
            )
        ],
        validation_report=ValidationReport(status="pass"),
        asset_id="asset_malformed",
        strategy_id="semantic_structural",
    )


@pytest.fixture
def chunk_set_ner_compatible() -> ChunkSet:
    """Fixture suitable for swapping to an alternate extractor strategy."""
    return ChunkSet(
        chunks=[
            _chunk(
                chunk_id="ck_ner",
                text="Entity Alpha interacts with Entity Beta.",
                element_type="paragraph",
            )
        ],
        validation_report=ValidationReport(status="pass"),
        asset_id="asset_ner",
        strategy_id="semantic_structural",
    )


@pytest.fixture
def chunk_set_50_chunks() -> ChunkSet:
    """Fifty-chunk fixture for latency budgeting (SC-008)."""
    chunks = [
        _chunk(
            chunk_id=f"ck_{i:03d}",
            text=f"Chunk number {i}. " + ("Content. " * 20),
            element_type="paragraph" if i % 5 else "heading",
            heading_path=[f"Section {i // 5}"],
            position=i,
        )
        for i in range(50)
    ]
    return ChunkSet(
        chunks=chunks,
        validation_report=ValidationReport(status="pass"),
        asset_id="asset_50_chunks",
        strategy_id="semantic_structural",
    )


def assert_package_unchanged(before, after) -> None:
    """SC-006 helper: package identity and counts must be identical."""
    assert before.metadata.package_id == after.metadata.package_id
    assert len(before.knowledge_units) == len(after.knowledge_units)
    assert len(before.knowledge_relationships) == len(after.knowledge_relationships)
    assert set(before.evidence_registry.keys()) == set(after.evidence_registry.keys())
