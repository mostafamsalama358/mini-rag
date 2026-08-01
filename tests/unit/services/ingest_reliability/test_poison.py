from services.ingest_reliability.poison import PoisonRegistry


def test_quarantine_after_threshold():
    reg = PoisonRegistry(threshold=2)
    r1 = reg.record_permanent_failure("doc", "v1")
    assert r1.disposition == "active"
    r2 = reg.record_permanent_failure("doc", "v1")
    assert r2.disposition == "quarantined"
    assert reg.is_quarantined("doc", "v1")


def test_clear_for_retry():
    reg = PoisonRegistry(threshold=1)
    reg.record_permanent_failure("doc", "v1")
    reg.clear_for_retry("doc", "v1")
    assert not reg.is_quarantined("doc", "v1")
