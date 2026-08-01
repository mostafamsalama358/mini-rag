"""Admission decisions (accept / delay / reject)."""

from __future__ import annotations

from dataclasses import dataclass

from helpers.config import Settings
from services.ingest_reliability.capacity import CapacityLedger
from services.ingest_reliability.models import (
    AdmissionOutcome,
    OperationalMode,
    WorkloadClass,
)


@dataclass(frozen=True)
class AdmissionDecision:
    outcome: AdmissionOutcome
    reason: str


class AdmissionController:
    def __init__(self, ledger: CapacityLedger, settings: Settings):
        self.ledger = ledger
        self.settings = settings

    def _mode(self) -> OperationalMode:
        raw = (self.settings.INGEST_OPERATIONAL_MODE or "normal").lower()
        try:
            return OperationalMode(raw)
        except ValueError:
            return OperationalMode.NORMAL

    def decide(self, workload_class: WorkloadClass, *, units: int = 1) -> AdmissionDecision:
        mode = self._mode()
        if mode == OperationalMode.ADMISSION_RESTRICTED:
            return AdmissionDecision(
                AdmissionOutcome.REJECT, "operational_mode_admission_restricted"
            )
        if mode == OperationalMode.MAINTENANCE:
            return AdmissionDecision(AdmissionOutcome.DELAY, "operational_mode_maintenance")

        self.ledger.max_concurrent = self.settings.INGEST_MAX_CONCURRENT_JOBS
        self.ledger.interactive_reserved = self.settings.INGEST_INTERACTIVE_RESERVED_SLOTS

        if self.ledger.can_accept(workload_class, units=units):
            return AdmissionDecision(AdmissionOutcome.ACCEPT, "capacity_available")

        # Soft backlog: if held < max + backlog, delay; else reject.
        held = self.ledger.held_units()
        if held < self.settings.INGEST_MAX_CONCURRENT_JOBS + self.settings.INGEST_MAX_BACKLOG:
            return AdmissionDecision(AdmissionOutcome.DELAY, "capacity_backpressure")
        return AdmissionDecision(AdmissionOutcome.REJECT, "capacity_exhausted")
