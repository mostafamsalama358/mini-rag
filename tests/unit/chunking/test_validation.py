"""US6: validation gate catches injected quality violations."""

from __future__ import annotations

from core.chunking.models import (
    Chunk,
    ChunkIdentity,
    ChunkLineage,
    ChunkRelationships,
    ChunkingStrategyConfig,
    StructuralContext,
)
from core.chunking.validator import ChunkValidator


def _make_chunk(**overrides) -> Chunk:
    base = Chunk(
        text="valid chunk text",
        metadata={
            "element_type": "paragraph",
            "source_element_ids": ["doc:p1"],
            "chunk_id": "ck_abc",
        },
        identity=ChunkIdentity(
            chunk_id="ck_abc",
            document_id="doc",
            strategy_id="semantic_structural",
            source_element_ids=["doc:p1"],
        ),
        relationships=ChunkRelationships(),
        lineage=ChunkLineage(
            source_element_ids=["doc:p1"],
            applied_rule="default_merge",
            triggered_features=["size_budget"],
            rationale="ok",
        ),
        structural_context=StructuralContext(element_type="paragraph", heading_path=[], position=0),
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_min_content_violation():
    validator = ChunkValidator(ChunkingStrategyConfig(max_chars=800))
    report = validator.validate([_make_chunk(text="   ")])
    assert "min_content" in report.failed_rules


def test_max_size_violation():
    validator = ChunkValidator(ChunkingStrategyConfig(max_chars=10))
    report = validator.validate([_make_chunk(text="x" * 50)])
    assert "max_size" in report.failed_rules


def test_referential_integrity_violation():
    chunk = _make_chunk()
    chunk.relationships.parent_chunk_id = "ck_missing"
    validator = ChunkValidator()
    report = validator.validate([chunk])
    assert "referential_integrity" in report.failed_rules


def test_validation_messages_present():
    validator = ChunkValidator(ChunkingStrategyConfig(max_chars=10))
    report = validator.validate([_make_chunk(text="x" * 50)])
    assert report.validation_messages


def test_validation_is_deterministic():
    validator = ChunkValidator(ChunkingStrategyConfig(max_chars=10))
    chunks = [_make_chunk(text="x" * 50)]
    first = validator.validate(chunks)
    second = validator.validate(chunks)
    assert first == second
