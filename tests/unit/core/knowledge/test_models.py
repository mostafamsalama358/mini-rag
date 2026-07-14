"""US3: model immutability and evidence traceability tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.chunking.models import ChunkSet
from core.knowledge.errors import EvidenceIntegrityError
from core.knowledge.extractors.structural import (
    StructuralKnowledgeUnitExtractor,
    build_evidence_reference,
)
from core.knowledge.models import (
    EvidenceReference,
    KnowledgeExtractionConfig,
    KnowledgeUnit,
    KnowledgeUnitMetadata,
    make_evidence_reference_id,
    utc_now_iso,
)


def test_evidence_traceability_all_levels(chunk_set_five_forms: ChunkSet) -> None:
    extractor = StructuralKnowledgeUnitExtractor()
    units = extractor.extract(chunk_set_five_forms, KnowledgeExtractionConfig())
    for unit in units:
        assert unit.evidence_references
        for ref in unit.evidence_references:
            assert ref.chunk_ids
            assert ref.element_ids
            assert ref.document_model_id
            assert ref.asset_id


def test_knowledge_unit_immutability(chunk_set_five_forms: ChunkSet) -> None:
    unit = StructuralKnowledgeUnitExtractor().extract(
        chunk_set_five_forms, KnowledgeExtractionConfig()
    )[0]
    with pytest.raises((ValidationError, TypeError, EvidenceIntegrityError)):
        unit.type = "fact"  # type: ignore[misc]


def test_evidence_reference_id_stability(chunk_set_five_forms: ChunkSet) -> None:
    chunk = chunk_set_five_forms.chunks[0]
    first = build_evidence_reference(chunk, chunk_set_five_forms)
    second = build_evidence_reference(chunk, chunk_set_five_forms)
    assert first.id == second.id
    expected = make_evidence_reference_id(
        chunk_ids=first.chunk_ids,
        element_ids=first.element_ids,
        document_model_id=first.document_model_id,
        asset_id=first.asset_id,
    )
    assert first.id == expected


def test_empty_evidence_rejected(chunk_set_five_forms: ChunkSet) -> None:
    chunk = chunk_set_five_forms.chunks[0]
    ref = build_evidence_reference(chunk, chunk_set_five_forms)
    with pytest.raises((EvidenceIntegrityError, ValidationError)):
        KnowledgeUnit(
            type="fact",
            semantic_content={"text": "x"},
            attributes={"source_surface_form": "x"},
            evidence_references=(),
            metadata=KnowledgeUnitMetadata(
                extractor_strategy_id="structural",
                created_at=utc_now_iso(),
                config_hash="abcd1234",
            ),
        )
    # partial ref rejected
    with pytest.raises((EvidenceIntegrityError, ValidationError)):
        EvidenceReference(
            chunk_ids=[],
            element_ids=ref.element_ids,
            document_model_id=ref.document_model_id,
            asset_id=ref.asset_id,
        )
