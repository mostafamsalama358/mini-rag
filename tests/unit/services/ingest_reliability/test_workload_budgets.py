from types import SimpleNamespace

from services.ingest_reliability.models import WorkloadClass
from services.ingest_reliability.workload import budget_for, resolve_workload_class


def _settings(**overrides):
    base = {
        "INGEST_LARGE_DOCUMENT_BYTES": 1_000_000,
        "INGEST_PARSE_TIMEOUT_SECONDS": 100,
        "INGEST_JOB_TIMEOUT_SECONDS": 200,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_resolve_large_vs_small():
    s = _settings()
    assert resolve_workload_class(999_999, s) == WorkloadClass.SMALL
    assert resolve_workload_class(1_000_000, s) == WorkloadClass.LARGE


def test_large_budget_tighter_memory():
    s = _settings()
    large = budget_for(WorkloadClass.LARGE, s)
    small = budget_for(WorkloadClass.SMALL, s)
    assert large.max_in_memory_bytes <= small.max_in_memory_bytes
    assert large.max_batch_elements <= small.max_batch_elements
