from types import SimpleNamespace

from services.ingest_reliability.admission import AdmissionController
from services.ingest_reliability.capacity import CapacityLedger
from services.ingest_reliability.models import AdmissionOutcome, WorkloadClass


def _settings(**kw):
    base = dict(
        INGEST_OPERATIONAL_MODE="normal",
        INGEST_MAX_CONCURRENT_JOBS=2,
        INGEST_MAX_BACKLOG=2,
        INGEST_INTERACTIVE_RESERVED_SLOTS=1,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_accept_when_capacity():
    ledger = CapacityLedger(max_concurrent=2, interactive_reserved=1)
    ctrl = AdmissionController(ledger, _settings())
    d = ctrl.decide(WorkloadClass.SMALL)
    assert d.outcome == AdmissionOutcome.ACCEPT


def test_reject_when_admission_restricted():
    ledger = CapacityLedger(max_concurrent=10, interactive_reserved=1)
    ctrl = AdmissionController(
        ledger, _settings(INGEST_OPERATIONAL_MODE="admission_restricted")
    )
    d = ctrl.decide(WorkloadClass.SMALL)
    assert d.outcome == AdmissionOutcome.REJECT


def test_delay_when_full_within_backlog():
    ledger = CapacityLedger(max_concurrent=1, interactive_reserved=0)
    ledger.hold(job_id="j1", workload_class=WorkloadClass.SMALL)
    ctrl = AdmissionController(ledger, _settings(INGEST_MAX_CONCURRENT_JOBS=1, INGEST_MAX_BACKLOG=5))
    d = ctrl.decide(WorkloadClass.SMALL)
    assert d.outcome == AdmissionOutcome.DELAY
