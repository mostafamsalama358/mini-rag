import pytest

from services.ingest_reliability.capacity import CapacityLedger, ClaimState
from services.ingest_reliability.models import WorkloadClass


def test_hold_and_release():
    ledger = CapacityLedger(max_concurrent=2, interactive_reserved=1)
    c1 = ledger.hold(job_id="j1", workload_class=WorkloadClass.SMALL)
    assert c1.state == ClaimState.HELD
    assert ledger.held_units() == 1
    ledger.release(c1.claim_id)
    assert ledger.held_units() == 0
    assert ledger.claims[c1.claim_id].state == ClaimState.RELEASED


def test_background_cannot_consume_interactive_reserve():
    ledger = CapacityLedger(max_concurrent=4, interactive_reserved=3)
    # Fill interactive headroom for background: max - reserved = 1
    ledger.hold(job_id="m1", workload_class=WorkloadClass.MAINTENANCE)
    with pytest.raises(RuntimeError):
        ledger.hold(job_id="m2", workload_class=WorkloadClass.MAINTENANCE)


def test_release_for_job():
    ledger = CapacityLedger(max_concurrent=5)
    ledger.hold(job_id="j1", workload_class=WorkloadClass.LARGE)
    assert ledger.release_for_job("j1") == 1
    assert ledger.held_units() == 0
