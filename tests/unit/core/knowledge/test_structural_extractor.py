"""US1/US2: StructuralKnowledgeUnitExtractor tests."""

from __future__ import annotations

from core.chunking.models import ChunkSet
from core.knowledge.extractors.structural import StructuralKnowledgeUnitExtractor
from core.knowledge.interfaces import KnowledgeUnitExtractor
from core.knowledge.models import (
    KnowledgeExtractionConfig,
    KnowledgeUnit,
    KnowledgeUnitMetadata,
    utc_now_iso,
)
from core.knowledge.pipeline import build_pipeline_from_config
from core.knowledge.registry import extractor_registry, register_defaults


def test_five_forms_correct_types(chunk_set_five_forms: ChunkSet) -> None:
    extractor = StructuralKnowledgeUnitExtractor()
    units = extractor.extract(chunk_set_five_forms, KnowledgeExtractionConfig())
    assert len(units) == 5
    types = [u.type for u in units]
    assert types == [
        "procedure",
        "definition",
        "measurement",
        "table",
        "assertion",
    ]
    for unit in units:
        assert unit.evidence_references
        assert "source_surface_form" in unit.attributes


def test_no_external_calls(chunk_set_five_forms: ChunkSet, monkeypatch) -> None:
    import urllib.request

    def boom(*_a, **_k):  # pragma: no cover - must never run
        raise AssertionError("external network call attempted")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    extractor = StructuralKnowledgeUnitExtractor()
    units = extractor.extract(chunk_set_five_forms, KnowledgeExtractionConfig())
    assert len(units) == 5


def test_ner_strategy_swappability(chunk_set_ner_compatible: ChunkSet) -> None:
    class StubAlternativeExtractor(KnowledgeUnitExtractor):
        @property
        def strategy_id(self) -> str:
            return "stub_alternative"

        def extract(self, chunk_set, config):
            return [
                KnowledgeUnit(
                    type="assertion",
                    semantic_content={"text": c.text},
                    attributes={"source_surface_form": c.text},
                    evidence_references=(
                        __import__(
                            "core.knowledge.extractors.structural",
                            fromlist=["build_evidence_reference"],
                        ).build_evidence_reference(c, chunk_set),
                    ),
                    metadata=KnowledgeUnitMetadata(
                        extractor_strategy_id=self.strategy_id,
                        created_at=utc_now_iso(),
                        config_hash="deadbeef",
                    ),
                )
                for c in chunk_set.chunks
            ]

    register_defaults()
    extractor_registry.register("stub_alternative", StubAlternativeExtractor())
    config = KnowledgeExtractionConfig(
        extractor_strategy="stub_alternative",
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
    )
    package = build_pipeline_from_config(config).run(chunk_set_ner_compatible, config)
    assert all(u.type == "assertion" for u in package.knowledge_units)


def test_strategy_swap_zero_core_change(chunk_set_five_forms: ChunkSet) -> None:
    class StubAlternativeExtractor(KnowledgeUnitExtractor):
        @property
        def strategy_id(self) -> str:
            return "stub_alternative"

        def extract(self, chunk_set, config):
            from core.knowledge.extractors.structural import build_evidence_reference

            return [
                KnowledgeUnit(
                    type="assertion",
                    semantic_content={"text": c.text},
                    attributes={"source_surface_form": c.text},
                    evidence_references=(build_evidence_reference(c, chunk_set),),
                    metadata=KnowledgeUnitMetadata(
                        extractor_strategy_id=self.strategy_id,
                        created_at=utc_now_iso(),
                        config_hash="cafebabe",
                    ),
                )
                for c in chunk_set.chunks
            ]

    register_defaults()
    extractor_registry.register("stub_alternative", StubAlternativeExtractor())
    config = KnowledgeExtractionConfig(
        extractor_strategy="stub_alternative",
        normalizer_strategy="passthrough",
        discoverer_strategy="noop",
    )
    package = build_pipeline_from_config(config).run(chunk_set_five_forms, config)
    assert len(package.knowledge_units) == 5
    assert all(u.type == "assertion" for u in package.knowledge_units)
    assert package.metadata.extractor_strategy_id == "stub_alternative"
    assert package.validation_report is not None
