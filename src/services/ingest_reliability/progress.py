"""Progress vs stall detection (FR-057)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from services.ingest_reliability.models import ProgressKind


@dataclass
class ProgressTracker:
    last_progress_at: datetime
    stall_seconds: int = 300
    kind: ProgressKind = ProgressKind.PROGRESSING

    def mark_progress(self) -> None:
        self.last_progress_at = datetime.now(timezone.utc)
        self.kind = ProgressKind.PROGRESSING

    def mark_waiting(self, reason: str = "") -> None:
        _ = reason
        self.kind = ProgressKind.WAITING
        # waiting does not advance last_progress_at, but also does not count as stall

    def evaluate(self, now: datetime | None = None) -> ProgressKind:
        now = now or datetime.now(timezone.utc)
        if self.kind == ProgressKind.WAITING:
            return ProgressKind.WAITING
        elapsed = (now - self.last_progress_at).total_seconds()
        if elapsed >= self.stall_seconds:
            self.kind = ProgressKind.STALLED
            return ProgressKind.STALLED
        return ProgressKind.PROGRESSING

    def should_escalate_timeout(self) -> bool:
        return self.evaluate() == ProgressKind.STALLED
