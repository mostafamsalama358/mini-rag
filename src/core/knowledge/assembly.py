"""Assemble a draft KnowledgePackage from units and relationships."""

from __future__ import annotations

from collections import Counter

from core.chunking.models import ChunkSet
from core.knowledge.models import (
    EvidenceReference,
    KnowledgeExtractionConfig,
    KnowledgePackage,
    KnowledgePackageMetadata,
    KnowledgePackageStatistics,
    KnowledgeRelationship,
    KnowledgeUnit,
    KnowledgeValidationMetadata,
    KnowledgeValidationReport,
    KnowledgeValidationStatistics,
    compute_config_hash,
    make_package_id,
    utc_now_iso,
)


class KnowledgePackageAssembler:
    """Build evidence registry, metadata, and statistics into a KnowledgePackage."""

    def assemble(
        self,
        units: list[KnowledgeUnit],
        relationships: list[KnowledgeRelationship],
        config: KnowledgeExtractionConfig,
        chunk_set: ChunkSet,
        *,
        extractor_strategy_id: str,
        normalizer_strategy_id: str,
        discoverer_strategy_id: str,
        validation_report: KnowledgeValidationReport | None = None,
    ) -> KnowledgePackage:
        config_hash = compute_config_hash(config)
        document_model_id = ""
        if chunk_set.chunks and chunk_set.chunks[0].identity is not None:
            document_model_id = chunk_set.chunks[0].identity.document_id

        package_id = make_package_id(
            asset_id=chunk_set.asset_id,
            extractor_id=extractor_strategy_id,
            normalizer_id=normalizer_strategy_id,
            discoverer_id=discoverer_strategy_id,
            config_hash=config_hash,
        )

        evidence_registry: dict[str, EvidenceReference] = {}
        for unit in units:
            for ref in unit.evidence_references:
                evidence_registry[ref.id] = ref
        for rel in relationships:
            for ref in rel.evidence_references:
                evidence_registry[ref.id] = ref

        referenced_chunk_ids: set[str] = set()
        for ref in evidence_registry.values():
            referenced_chunk_ids.update(ref.chunk_ids)
        total_chunks = len(chunk_set.chunks)
        coverage = (
            (len(referenced_chunk_ids) / total_chunks) * 100.0 if total_chunks else 0.0
        )

        if validation_report is None:
            validation_report = KnowledgeValidationReport(
                status="passed",
                errors=(),
                warnings=(),
                validation_results=(),
                statistics=KnowledgeValidationStatistics(
                    total_units_checked=len(units),
                    total_relationships_checked=len(relationships),
                ),
                metadata=KnowledgeValidationMetadata(
                    chunk_set_id=chunk_set.asset_id,
                    knowledge_package_id=package_id,
                    validated_at=utc_now_iso(),
                ),
            )

        unit_counts = dict(Counter(u.type for u in units))
        rel_counts = dict(Counter(r.relationship_type for r in relationships))
        pass_count = sum(
            1 for r in validation_report.validation_results if r.outcome == "pass"
        )

        return KnowledgePackage(
            knowledge_units=tuple(units),
            knowledge_relationships=tuple(relationships),
            evidence_registry=evidence_registry,
            validation_report=validation_report,
            metadata=KnowledgePackageMetadata(
                package_id=package_id,
                chunk_set_asset_id=chunk_set.asset_id,
                document_model_id=document_model_id,
                asset_id=chunk_set.asset_id,
                extractor_strategy_id=extractor_strategy_id,
                normalizer_strategy_id=normalizer_strategy_id,
                discoverer_strategy_id=discoverer_strategy_id,
                config_hash=config_hash,
                created_at=utc_now_iso(),
            ),
            statistics=KnowledgePackageStatistics(
                unit_counts_by_type=unit_counts,
                relationship_counts_by_type=rel_counts,
                evidence_coverage_pct=coverage,
                validation_pass_count=pass_count,
                validation_error_count=len(validation_report.errors),
                validation_warning_count=len(validation_report.warnings),
            ),
        )
