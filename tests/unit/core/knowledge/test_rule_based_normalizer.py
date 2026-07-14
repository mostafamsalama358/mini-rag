"""US4: RuleBasedKnowledgeNormalizer tests."""

from __future__ import annotations

from core.chunking.models import ChunkSet
from core.knowledge.extractors.structural import StructuralKnowledgeUnitExtractor
from core.knowledge.models import KnowledgeExtractionConfig
from core.knowledge.normalizers.rule_based import RuleBasedKnowledgeNormalizer


def _extract(chunk_set: ChunkSet):
    return StructuralKnowledgeUnitExtractor().extract(
        chunk_set, KnowledgeExtractionConfig()
    )


def test_alias_deduplication(chunk_set_alias_pair: ChunkSet) -> None:
    units = _extract(chunk_set_alias_pair)
    config = KnowledgeExtractionConfig(
        normalizer_params={
            "alias_map": {"asa": "acetylsalicylic acid"},
        }
    )
    normalized = RuleBasedKnowledgeNormalizer().normalize(units, config)
    assert len(normalized) == 1
    assert normalized[0].metadata.normalization_status == "merged"
    assert len(normalized[0].evidence_references) == 2


def test_exact_match_deduplication(chunk_set_alias_pair: ChunkSet) -> None:
    units = _extract(chunk_set_alias_pair)
    # Force identical surface forms
    twin = units[0].model_copy(
        update={
            "semantic_content": dict(units[0].semantic_content),
            "attributes": dict(units[0].attributes),
        }
    )
    # Can't model_copy frozen with id reuse easily — re-normalize pair of identical text
    units[1]  # ensure fixture has two
    identical = [
        units[0],
        units[0].__class__(
            type=units[0].type,
            semantic_content=dict(units[0].semantic_content),
            participants=units[0].participants,
            attributes=dict(units[0].attributes),
            evidence_references=units[1].evidence_references,
            metadata=units[0].metadata,
        ),
    ]
    normalized = RuleBasedKnowledgeNormalizer().normalize(
        identical, KnowledgeExtractionConfig()
    )
    assert len(normalized) == 1
    assert len(normalized[0].evidence_references) == 2


def test_normalization_preserves_all_evidence(chunk_set_alias_pair: ChunkSet) -> None:
    units = _extract(chunk_set_alias_pair)
    config = KnowledgeExtractionConfig(
        normalizer_params={"alias_map": {"asa": "acetylsalicylic acid"}}
    )
    before_ids = {ref.id for u in units for ref in u.evidence_references}
    normalized = RuleBasedKnowledgeNormalizer().normalize(units, config)
    after_ids = {ref.id for u in normalized for ref in u.evidence_references}
    assert before_ids == after_ids


def test_normalization_does_not_create_relationships(
    chunk_set_alias_pair: ChunkSet,
) -> None:
    units = _extract(chunk_set_alias_pair)
    normalized = RuleBasedKnowledgeNormalizer().normalize(
        units, KnowledgeExtractionConfig()
    )
    for unit in normalized:
        assert unit.relationships == ()


def test_normalization_is_deterministic(chunk_set_alias_pair: ChunkSet) -> None:
    units = _extract(chunk_set_alias_pair)
    config = KnowledgeExtractionConfig(
        normalizer_params={"alias_map": {"asa": "acetylsalicylic acid"}}
    )
    normalizer = RuleBasedKnowledgeNormalizer()
    first = normalizer.normalize(units, config)
    second = normalizer.normalize(units, config)
    assert [u.id for u in first] == [u.id for u in second]
    assert [len(u.evidence_references) for u in first] == [
        len(u.evidence_references) for u in second
    ]
