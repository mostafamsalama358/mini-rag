"""KnowledgeValidator — named quality rules (FR-024 / FR-025)."""

from __future__ import annotations

from core.chunking.models import ChunkSet
from core.knowledge.models import (
    KNOWLEDGE_UNIT_TYPES,
    KnowledgePackage,
    KnowledgeValidationMetadata,
    KnowledgeValidationReport,
    KnowledgeValidationStatistics,
    ValidationRuleResult,
    utc_now_iso,
)


class KnowledgeValidator:
    """Apply named quality rules and produce an immutable validation report."""

    RULE_SET_VERSION = "1.0.0"

    def validate(
        self,
        draft_package: KnowledgePackage,
        chunk_set: ChunkSet,
        document_model_id: str,
        *,
        max_units: int | None = None,
    ) -> KnowledgeValidationReport:
        _ = document_model_id
        results: list[ValidationRuleResult] = []
        results.append(self._rule_evidence_non_empty(draft_package))
        results.append(self._rule_reference_resolution(draft_package, chunk_set))
        results.append(self._rule_dangling_unit_reference(draft_package))
        results.append(self._rule_recognized_unit_type(draft_package))
        results.append(self._rule_full_traceability_chain(draft_package))
        results.append(self.check_max_units(draft_package, max_units))
        results.append(self._rule_unit_without_semantic_content(draft_package))

        errors = tuple(r for r in results if r.outcome == "error")
        warnings = tuple(r for r in results if r.outcome == "warning")
        if errors:
            status = "failed"
        elif warnings:
            status = "passed_with_warnings"
        else:
            status = "passed"

        return KnowledgeValidationReport(
            status=status,
            errors=errors,
            warnings=warnings,
            validation_results=tuple(results),
            statistics=KnowledgeValidationStatistics(
                total_units_checked=len(draft_package.knowledge_units),
                total_relationships_checked=len(draft_package.knowledge_relationships),
                error_count=len(errors),
                warning_count=len(warnings),
                auto_correction_count=0,
            ),
            metadata=KnowledgeValidationMetadata(
                chunk_set_id=chunk_set.asset_id,
                knowledge_package_id=draft_package.metadata.package_id,
                validated_at=utc_now_iso(),
                rule_set_version=self.RULE_SET_VERSION,
            ),
        )

    def _rule_evidence_non_empty(self, package: KnowledgePackage) -> ValidationRuleResult:
        bad_units = [u.id for u in package.knowledge_units if not u.evidence_references]
        bad_rels = [
            r.id for r in package.knowledge_relationships if not r.evidence_references
        ]
        if bad_units or bad_rels:
            return ValidationRuleResult(
                rule_id="evidence_non_empty",
                outcome="error",
                implicated_unit_ids=bad_units,
                implicated_relationship_ids=bad_rels,
                message="One or more units/relationships have empty evidence_references",
            )
        return ValidationRuleResult(
            rule_id="evidence_non_empty",
            outcome="pass",
            message="All evidence collections are non-empty",
        )

    def _rule_reference_resolution(
        self, package: KnowledgePackage, chunk_set: ChunkSet
    ) -> ValidationRuleResult:
        known_chunks = {
            c.identity.chunk_id
            for c in chunk_set.chunks
            if c.identity is not None
        }
        known_elements: set[str] = set()
        for chunk in chunk_set.chunks:
            if chunk.identity is not None:
                known_elements.update(chunk.identity.source_element_ids)

        bad_units: list[str] = []
        for unit in package.knowledge_units:
            for ref in unit.evidence_references:
                if any(cid not in known_chunks for cid in ref.chunk_ids):
                    bad_units.append(unit.id)
                    break
                if any(eid not in known_elements for eid in ref.element_ids):
                    bad_units.append(unit.id)
                    break
        if bad_units:
            return ValidationRuleResult(
                rule_id="reference_resolution",
                outcome="error",
                implicated_unit_ids=bad_units,
                message="Evidence references unresolved chunk or element ids",
            )
        return ValidationRuleResult(
            rule_id="reference_resolution",
            outcome="pass",
            message="All evidence references resolve against the ChunkSet",
        )

    def _rule_dangling_unit_reference(
        self, package: KnowledgePackage
    ) -> ValidationRuleResult:
        unit_ids = {u.id for u in package.knowledge_units}
        bad_rels = [
            r.id
            for r in package.knowledge_relationships
            if r.source_unit_id not in unit_ids or r.target_unit_id not in unit_ids
        ]
        if bad_rels:
            return ValidationRuleResult(
                rule_id="dangling_unit_reference",
                outcome="error",
                implicated_relationship_ids=bad_rels,
                message="Relationship references unknown KnowledgeUnit ids",
            )
        return ValidationRuleResult(
            rule_id="dangling_unit_reference",
            outcome="pass",
            message="All relationship endpoints resolve to package units",
        )

    def _rule_recognized_unit_type(
        self, package: KnowledgePackage
    ) -> ValidationRuleResult:
        bad_units = [
            u.id for u in package.knowledge_units if u.type not in KNOWLEDGE_UNIT_TYPES
        ]
        if bad_units:
            return ValidationRuleResult(
                rule_id="recognized_unit_type",
                outcome="error",
                implicated_unit_ids=bad_units,
                message="One or more units use an unrecognized type",
            )
        return ValidationRuleResult(
            rule_id="recognized_unit_type",
            outcome="pass",
            message="All unit types are recognized",
        )

    def _rule_full_traceability_chain(
        self, package: KnowledgePackage
    ) -> ValidationRuleResult:
        bad_units: list[str] = []
        for unit in package.knowledge_units:
            for ref in unit.evidence_references:
                if (
                    not ref.chunk_ids
                    or not ref.element_ids
                    or not ref.document_model_id
                    or not ref.asset_id
                ):
                    bad_units.append(unit.id)
                    break
        if bad_units:
            return ValidationRuleResult(
                rule_id="full_traceability_chain",
                outcome="error",
                implicated_unit_ids=bad_units,
                message="EvidenceReference missing one or more traceability levels",
            )
        return ValidationRuleResult(
            rule_id="full_traceability_chain",
            outcome="pass",
            message="All evidence references carry the four-level chain",
        )

    def check_max_units(
        self, package: KnowledgePackage, max_units: int | None
    ) -> ValidationRuleResult:
        if max_units is not None and len(package.knowledge_units) > max_units:
            return ValidationRuleResult(
                rule_id="max_unit_count_exceeded",
                outcome="warning",
                implicated_unit_ids=[u.id for u in package.knowledge_units],
                message=f"Unit count {len(package.knowledge_units)} exceeds max_units={max_units}",
            )
        return ValidationRuleResult(
            rule_id="max_unit_count_exceeded",
            outcome="pass",
            message="max_units not exceeded (or not configured)",
        )

    def _rule_unit_without_semantic_content(
        self, package: KnowledgePackage
    ) -> ValidationRuleResult:
        bad_units = [
            u.id for u in package.knowledge_units if not u.semantic_content
        ]
        if bad_units:
            return ValidationRuleResult(
                rule_id="unit_without_semantic_content",
                outcome="warning",
                implicated_unit_ids=bad_units,
                message="One or more units have empty semantic_content",
            )
        return ValidationRuleResult(
            rule_id="unit_without_semantic_content",
            outcome="pass",
            message="All units have semantic_content",
        )
