"""Poison quarantine and dead-letter disposition."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PoisonRecord:
    logical_document_id: str
    version_id: str
    permanent_failures: int = 0
    disposition: str = "active"  # active | quarantined | cleared_for_retry | discarded | terminal
    dead_letter: bool = False
    metadata: dict = field(default_factory=dict)


class PoisonRegistry:
    """In-process registry; durable store can mirror these records later."""

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._records: dict[tuple[str, str], PoisonRecord] = {}

    def _key(self, logical_document_id: str, version_id: str) -> tuple[str, str]:
        return (logical_document_id, version_id)

    def record_permanent_failure(
        self, logical_document_id: str, version_id: str, *, detail: str = ""
    ) -> PoisonRecord:
        key = self._key(logical_document_id, version_id)
        rec = self._records.get(key) or PoisonRecord(logical_document_id, version_id)
        rec.permanent_failures += 1
        if detail:
            rec.metadata["last_detail"] = detail
        if rec.permanent_failures >= self.threshold:
            rec.disposition = "quarantined"
            rec.dead_letter = True
        self._records[key] = rec
        return rec

    def is_quarantined(self, logical_document_id: str, version_id: str) -> bool:
        rec = self._records.get(self._key(logical_document_id, version_id))
        return bool(rec and rec.disposition == "quarantined")

    def clear_for_retry(self, logical_document_id: str, version_id: str) -> None:
        key = self._key(logical_document_id, version_id)
        rec = self._records.get(key)
        if rec:
            rec.disposition = "cleared_for_retry"
            rec.permanent_failures = 0
            rec.dead_letter = False


DEFAULT_POISON_REGISTRY = PoisonRegistry()
