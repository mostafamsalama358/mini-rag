"""Operational mode manager."""

from __future__ import annotations

from helpers.config import Settings
from services.ingest_reliability.models import OperationalMode


def current_mode(settings: Settings) -> OperationalMode:
    raw = (settings.INGEST_OPERATIONAL_MODE or "normal").lower()
    try:
        return OperationalMode(raw)
    except ValueError:
        return OperationalMode.NORMAL


def admission_allowed(mode: OperationalMode) -> bool:
    return mode not in (
        OperationalMode.ADMISSION_RESTRICTED,
        # Maintenance delays rather than hard-blocks in AdmissionController
    )


def describe_mode(mode: OperationalMode) -> str:
    return {
        OperationalMode.NORMAL: "Full admission within capacity",
        OperationalMode.DEGRADED: "Impaired dependencies; explicit degrade/fail-fast",
        OperationalMode.MAINTENANCE: "Admission delayed; in-flight drain",
        OperationalMode.RECOVERY: "Orphan recovery prioritized; admission tightened",
        OperationalMode.ADMISSION_RESTRICTED: "New work rejected with mode signal",
    }[mode]
