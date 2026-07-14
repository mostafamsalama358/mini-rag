"""Pydantic models for the Knowledge Representation pipeline (spec 008)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.knowledge.errors import EvidenceIntegrityError

KnowledgeUnitType = Literal[
    "fact",
    "procedure",
    "rule",
    "definition",
    "measurement",
    "list",
    "table",
    "assertion",
    "structured_observation",
]

KNOWLEDGE_UNIT_TYPES: frozenset[str] = frozenset(
    {
        "fact",
        "procedure",
        "rule",
        "definition",
        "measurement",
        "list",
        "table",
        "assertion",
        "structured_observation",
    }
)

KnowledgeRelationshipType = Literal[
    "dependency",
    "equivalence",
    "contradiction",
    "elaboration",
    "containment",
    "sequence",
    "derivation",
]

KnowledgeValidationStatus = Literal["passed", "passed_with_warnings", "failed"]
ValidationRuleOutcome = Literal["pass", "error", "warning"]
NormalizationStatus = Literal["raw", "normalized", "merged"]


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_config_hash(config: KnowledgeExtractionConfig) -> str:
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def make_evidence_reference_id(
    *,
    chunk_ids: list[str],
    element_ids: list[str],
    document_model_id: str,
    asset_id: str,
) -> str:
    payload = (
        f"{sorted(chunk_ids)}|{sorted(element_ids)}|{document_model_id}|{asset_id}"
    )
    return f"er_{_sha16(payload)}"


def make_knowledge_unit_id(
    *,
    evidence_ref_ids: list[str],
    unit_type: str,
    strategy_id: str,
    config_hash: str,
) -> str:
    payload = f"{sorted(evidence_ref_ids)}|{unit_type}|{strategy_id}|{config_hash}"
    return f"ku_{_sha16(payload)}"


def make_knowledge_relationship_id(
    *,
    source_unit_id: str,
    target_unit_id: str,
    relationship_type: str,
    strategy_id: str,
) -> str:
    payload = f"{source_unit_id}|{target_unit_id}|{relationship_type}|{strategy_id}"
    return f"kr_{_sha16(payload)}"


def make_package_id(
    *,
    asset_id: str,
    extractor_id: str,
    normalizer_id: str,
    discoverer_id: str,
    config_hash: str,
) -> str:
    payload = f"{asset_id}|{extractor_id}|{normalizer_id}|{discoverer_id}|{config_hash}"
    return f"kp_{_sha16(payload)}"


def _assert_full_traceability(ref: EvidenceReference) -> EvidenceReference:
    if not ref.chunk_ids:
        raise EvidenceIntegrityError("EvidenceReference.chunk_ids must be non-empty")
    if not ref.element_ids:
        raise EvidenceIntegrityError("EvidenceReference.element_ids must be non-empty")
    if not ref.document_model_id:
        raise EvidenceIntegrityError(
            "EvidenceReference.document_model_id must be non-empty"
        )
    if not ref.asset_id:
        raise EvidenceIntegrityError("EvidenceReference.asset_id must be non-empty")
    return ref


class EvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    chunk_ids: list[str]
    element_ids: list[str]
    document_model_id: str
    asset_id: str

    @model_validator(mode="before")
    @classmethod
    def _ensure_id(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("id"):
            return data
        chunk_ids = list(data.get("chunk_ids") or [])
        element_ids = list(data.get("element_ids") or [])
        document_model_id = str(data.get("document_model_id") or "")
        asset_id = str(data.get("asset_id") or "")
        data = dict(data)
        data["id"] = make_evidence_reference_id(
            chunk_ids=chunk_ids,
            element_ids=element_ids,
            document_model_id=document_model_id,
            asset_id=asset_id,
        )
        return data

    @field_validator("chunk_ids", "element_ids")
    @classmethod
    def _non_empty_lists(cls, value: list[str]) -> list[str]:
        if not value:
            raise EvidenceIntegrityError("traceability list fields must be non-empty")
        return value

    @field_validator("document_model_id", "asset_id")
    @classmethod
    def _non_empty_strings(cls, value: str) -> str:
        if not value:
            raise EvidenceIntegrityError("traceability string fields must be non-empty")
        return value


class KnowledgeUnitMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    extractor_strategy_id: str
    normalization_status: NormalizationStatus = "raw"
    created_at: str = Field(default_factory=utc_now_iso)
    config_hash: str


class KnowledgeRelationshipMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    discoverer_strategy_id: str
    created_at: str = Field(default_factory=utc_now_iso)


class KnowledgeUnit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    type: KnowledgeUnitType
    semantic_content: dict[str, Any]
    participants: dict[str, Any] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_references: tuple[EvidenceReference, ...]
    relationships: tuple[str, ...] = ()
    metadata: KnowledgeUnitMetadata

    @model_validator(mode="before")
    @classmethod
    def _ensure_id(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("id"):
            return data
        refs = data.get("evidence_references") or ()
        ref_ids: list[str] = []
        for ref in refs:
            if isinstance(ref, EvidenceReference):
                ref_ids.append(ref.id)
            elif isinstance(ref, dict):
                ref_ids.append(
                    str(
                        ref.get("id")
                        or make_evidence_reference_id(
                            chunk_ids=list(ref.get("chunk_ids") or []),
                            element_ids=list(ref.get("element_ids") or []),
                            document_model_id=str(ref.get("document_model_id") or ""),
                            asset_id=str(ref.get("asset_id") or ""),
                        )
                    )
                )
        meta = data.get("metadata") or {}
        if isinstance(meta, KnowledgeUnitMetadata):
            strategy_id = meta.extractor_strategy_id
            config_hash = meta.config_hash
        else:
            strategy_id = str(meta.get("extractor_strategy_id") or "")
            config_hash = str(meta.get("config_hash") or "")
        data = dict(data)
        data["id"] = make_knowledge_unit_id(
            evidence_ref_ids=ref_ids,
            unit_type=str(data.get("type") or ""),
            strategy_id=strategy_id,
            config_hash=config_hash,
        )
        return data

    @field_validator("evidence_references")
    @classmethod
    def _validate_evidence(
        cls, value: tuple[EvidenceReference, ...]
    ) -> tuple[EvidenceReference, ...]:
        if not value:
            raise EvidenceIntegrityError(
                "KnowledgeUnit.evidence_references must be non-empty"
            )
        for ref in value:
            _assert_full_traceability(ref)
        return value


class KnowledgeRelationship(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    relationship_type: KnowledgeRelationshipType
    source_unit_id: str
    target_unit_id: str
    evidence_references: tuple[EvidenceReference, ...]
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: KnowledgeRelationshipMetadata

    @model_validator(mode="before")
    @classmethod
    def _ensure_id(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("id"):
            return data
        meta = data.get("metadata") or {}
        if isinstance(meta, KnowledgeRelationshipMetadata):
            strategy_id = meta.discoverer_strategy_id
        else:
            strategy_id = str(meta.get("discoverer_strategy_id") or "")
        data = dict(data)
        data["id"] = make_knowledge_relationship_id(
            source_unit_id=str(data.get("source_unit_id") or ""),
            target_unit_id=str(data.get("target_unit_id") or ""),
            relationship_type=str(data.get("relationship_type") or ""),
            strategy_id=strategy_id,
        )
        return data

    @model_validator(mode="after")
    def _no_self_ref(self) -> KnowledgeRelationship:
        if self.source_unit_id == self.target_unit_id:
            raise ValueError("source_unit_id must differ from target_unit_id")
        return self

    @field_validator("evidence_references")
    @classmethod
    def _validate_evidence(
        cls, value: tuple[EvidenceReference, ...]
    ) -> tuple[EvidenceReference, ...]:
        if not value:
            raise EvidenceIntegrityError(
                "KnowledgeRelationship.evidence_references must be non-empty"
            )
        for ref in value:
            _assert_full_traceability(ref)
        return value


class RelationshipCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_unit_id: str
    target_unit_id: str
    relationship_type: KnowledgeRelationshipType
    evidence_references: tuple[EvidenceReference, ...]
    rationale: str
    score: float | None = None


class ValidationRuleResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    outcome: ValidationRuleOutcome
    implicated_unit_ids: list[str] = Field(default_factory=list)
    implicated_relationship_ids: list[str] = Field(default_factory=list)
    message: str


class KnowledgeValidationStatistics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_units_checked: int = 0
    total_relationships_checked: int = 0
    error_count: int = 0
    warning_count: int = 0
    auto_correction_count: int = 0


class KnowledgeValidationMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_set_id: str
    knowledge_package_id: str
    validated_at: str = Field(default_factory=utc_now_iso)
    rule_set_version: str = "1.0.0"


class KnowledgeValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: KnowledgeValidationStatus
    errors: tuple[ValidationRuleResult, ...] = ()
    warnings: tuple[ValidationRuleResult, ...] = ()
    validation_results: tuple[ValidationRuleResult, ...] = ()
    statistics: KnowledgeValidationStatistics
    metadata: KnowledgeValidationMetadata

    @model_validator(mode="after")
    def _status_matches_counts(self) -> KnowledgeValidationReport:
        if self.errors and self.status != "failed":
            raise ValueError("status must be 'failed' when errors are present")
        if not self.errors and self.warnings and self.status != "passed_with_warnings":
            raise ValueError(
                "status must be 'passed_with_warnings' when only warnings are present"
            )
        if not self.errors and not self.warnings and self.status != "passed":
            raise ValueError("status must be 'passed' when there are no issues")
        return self


class KnowledgePackageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    package_id: str
    chunk_set_asset_id: str
    document_model_id: str
    asset_id: str
    extractor_strategy_id: str
    normalizer_strategy_id: str
    discoverer_strategy_id: str
    config_hash: str
    created_at: str = Field(default_factory=utc_now_iso)


class KnowledgePackageStatistics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_counts_by_type: dict[str, int] = Field(default_factory=dict)
    relationship_counts_by_type: dict[str, int] = Field(default_factory=dict)
    evidence_coverage_pct: float = 0.0
    validation_pass_count: int = 0
    validation_error_count: int = 0
    validation_warning_count: int = 0


class KnowledgePackage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    knowledge_units: tuple[KnowledgeUnit, ...]
    knowledge_relationships: tuple[KnowledgeRelationship, ...]
    evidence_registry: dict[str, EvidenceReference]
    validation_report: KnowledgeValidationReport
    metadata: KnowledgePackageMetadata
    statistics: KnowledgePackageStatistics


class KnowledgeExtractionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extractor_strategy: str = "structural"
    normalizer_strategy: str = "rule_based"
    discoverer_strategy: str = "structural"
    representation_strategies: list[str] = Field(default_factory=list)
    max_units: int | None = None
    extractor_params: dict[str, Any] = Field(default_factory=dict)
    normalizer_params: dict[str, Any] = Field(default_factory=dict)
    discoverer_params: dict[str, Any] = Field(default_factory=dict)
    fail_on_error: bool = False
