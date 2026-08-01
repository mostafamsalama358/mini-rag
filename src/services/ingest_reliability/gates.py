"""Validation / integrity / security gates (spec 017)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from helpers.config import Settings
from services.ingest_reliability.models import FailureOwnership


@dataclass(frozen=True)
class GateResult:
    passed: bool
    gate_name: str
    reason: str = ""
    ownership: Optional[FailureOwnership] = None


def hard_size_gate(size_bytes: int, settings: Settings) -> GateResult:
    hard_max = settings.INGEST_HARD_MAX_BYTES
    if hard_max <= 0:
        hard_max = int(settings.FILE_MAX_SIZE) * 1024 * 1024
    if hard_max > 0 and size_bytes > hard_max:
        return GateResult(
            False,
            "hard_size",
            reason="hard_max_bytes",
            ownership=FailureOwnership.USER_INPUT,
        )
    return GateResult(True, "hard_size")


def minimum_usable_content_gate(
    *,
    element_count: int,
    text_chars: int,
    min_elements: int = 1,
    min_chars: int = 1,
) -> GateResult:
    if element_count >= min_elements and text_chars >= min_chars:
        return GateResult(True, "minimum_usable_content")
    return GateResult(
        False,
        "minimum_usable_content",
        reason="empty_or_unusable_content",
        ownership=FailureOwnership.DOCUMENT_QUALITY,
    )


def tenant_ownership_gate(
    *,
    project_id: int,
    asset_project_id: Optional[int],
) -> GateResult:
    if asset_project_id is None:
        return GateResult(
            False,
            "tenant_ownership",
            reason="asset_missing",
            ownership=FailureOwnership.USER_INPUT,
        )
    if int(asset_project_id) != int(project_id):
        return GateResult(
            False,
            "tenant_ownership",
            reason="project_mismatch",
            ownership=FailureOwnership.USER_INPUT,
        )
    return GateResult(True, "tenant_ownership")


def integrity_pre_publish_gate(
    *,
    has_searchable_units: bool,
    metadata_complete: bool,
    version_consistent: bool,
) -> GateResult:
    if has_searchable_units and metadata_complete and version_consistent:
        return GateResult(True, "integrity_pre_publish")
    reasons = []
    if not has_searchable_units:
        reasons.append("no_searchable_units")
    if not metadata_complete:
        reasons.append("metadata_incomplete")
    if not version_consistent:
        reasons.append("version_inconsistent")
    return GateResult(
        False,
        "integrity_pre_publish",
        reason=",".join(reasons),
        ownership=FailureOwnership.PLATFORM,
    )
