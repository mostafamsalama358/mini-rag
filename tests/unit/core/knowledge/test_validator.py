"""US6: KnowledgeValidator tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.chunking.models import ChunkSet
from core.knowledge.models import (
    KnowledgeExtractionConfig,
    KnowledgePackage,
    KnowledgeRelationship,
    KnowledgeRelationshipMetadata,
    KnowledgeUnit,
    utc_now_iso,
)
from core.knowledge.pipeline import build_pipeline_from_config
from core.knowledge.validation import KnowledgeValidator


def _clean_package(chunk_set: ChunkSet) -> KnowledgePackage:
    config = KnowledgeExtractionConfig(
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
    )
    return build_pipeline_from_config(config).run(chunk_set, config)


def test_malformed_inputs_caught(chunk_set_malformed: ChunkSet) -> None:
    clean = _clean_package(chunk_set_malformed)
    unit = clean.knowledge_units[0]
    ghost_ref = unit.evidence_references[0]

    empty_evidence_unit = KnowledgeUnit.model_construct(
        id="ku_empty_ev",
        type="fact",
        semantic_content={"text": "x"},
        participants=None,
        attributes={"source_surface_form": "x"},
        evidence_references=(),
        relationships=(),
        metadata=unit.metadata,
    )
    alien_unit = KnowledgeUnit.model_construct(
        id="ku_alien",
        type="alien_type",  # type: ignore[arg-type]
        semantic_content={"text": "y"},
        participants=None,
        attributes={"source_surface_form": "y"},
        evidence_references=unit.evidence_references,
        relationships=(),
        metadata=unit.metadata,
    )
    dangling_rel = KnowledgeRelationship.model_construct(
        id="kr_ghost",
        relationship_type="sequence",
        source_unit_id="ku_ghost",
        target_unit_id=unit.id,
        evidence_references=(ghost_ref,),
        attributes={},
        metadata=KnowledgeRelationshipMetadata(
            discoverer_strategy_id="structural",
            created_at=utc_now_iso(),
        ),
    )

    draft = KnowledgePackage.model_construct(
        knowledge_units=(empty_evidence_unit, alien_unit, unit),
        knowledge_relationships=(dangling_rel,),
        evidence_registry=dict(clean.evidence_registry),
        validation_report=clean.validation_report,
        metadata=clean.metadata,
        statistics=clean.statistics,
    )
    report = KnowledgeValidator().validate(
        draft, chunk_set_malformed, clean.metadata.document_model_id
    )
    error_ids = {e.rule_id for e in report.errors}
    assert "evidence_non_empty" in error_ids
    assert "dangling_unit_reference" in error_ids
    assert "recognized_unit_type" in error_ids


def test_validation_report_always_present(chunk_set_five_forms: ChunkSet) -> None:
    package = _clean_package(chunk_set_five_forms)
    assert package.validation_report is not None
    assert package.validation_report.status in {
        "passed",
        "passed_with_warnings",
        "failed",
    }


def test_passed_status_on_clean_package(chunk_set_five_forms: ChunkSet) -> None:
    package = _clean_package(chunk_set_five_forms)
    assert package.validation_report.status in {"passed", "passed_with_warnings"}
    assert package.validation_report.errors == ()


def test_warning_on_max_unit_exceeded(chunk_set_five_forms: ChunkSet) -> None:
    package = _clean_package(chunk_set_five_forms)
    result = KnowledgeValidator().check_max_units(package, max_units=1)
    assert result.outcome == "warning"
    assert result.rule_id == "max_unit_count_exceeded"


def test_report_immutable_after_production(chunk_set_five_forms: ChunkSet) -> None:
    package = _clean_package(chunk_set_five_forms)
    report = package.validation_report
    with pytest.raises((ValidationError, TypeError)):
        report.status = "failed"  # type: ignore[misc]
