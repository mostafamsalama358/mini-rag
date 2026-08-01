from datetime import datetime, timedelta, timezone

from services.ingest_reliability.models import ProgressKind
from services.ingest_reliability.progress import ProgressTracker


def test_stall_escalation():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tracker = ProgressTracker(last_progress_at=t0, stall_seconds=60)
    assert tracker.evaluate(t0 + timedelta(seconds=30)) == ProgressKind.PROGRESSING
    assert tracker.evaluate(t0 + timedelta(seconds=61)) == ProgressKind.STALLED
    assert tracker.should_escalate_timeout()


def test_waiting_not_stalled():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tracker = ProgressTracker(last_progress_at=t0, stall_seconds=10)
    tracker.mark_waiting("backpressure")
    assert tracker.evaluate(t0 + timedelta(seconds=100)) == ProgressKind.WAITING
