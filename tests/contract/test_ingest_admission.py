"""Contract tests for admission outcomes (contracts/admission-capacity.md)."""

from types import SimpleNamespace

from services.ingest_reliability.admission import AdmissionController
from services.ingest_reliability.capacity import CapacityLedger
from services.ingest_reliability.models import AdmissionOutcome, WorkloadClass


def test_admission_outcomes_are_explicit():
    settings = SimpleNamespace(
        INGEST_OPERATIONAL_MODE="normal",
        INGEST_MAX_CONCURRENT_JOBS=1,
        INGEST_MAX_BACKLOG=0,
        INGEST_INTERACTIVE_RESERVED_SLOTS=0,
    )
    ledger = CapacityLedger(max_concurrent=1, interactive_reserved=0)
    ctrl = AdmissionController(ledger, settings)
    assert ctrl.decide(WorkloadClass.SMALL).outcome == AdmissionOutcome.ACCEPT
    ledger.hold(job_id="j1", workload_class=WorkloadClass.SMALL)
    # backlog 0 → reject when full
    assert ctrl.decide(WorkloadClass.SMALL).outcome == AdmissionOutcome.REJECT
