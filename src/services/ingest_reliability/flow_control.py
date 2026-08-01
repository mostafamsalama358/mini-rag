"""Inter-stage flow control (back-pressure between stages)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StageFlowController:
    """Simple in-flight permit limiter between producer/consumer stages."""

    max_in_flight: int = 4
    _in_flight: int = 0

    def try_acquire(self) -> bool:
        if self._in_flight >= self.max_in_flight:
            return False
        self._in_flight += 1
        return True

    def release(self) -> None:
        if self._in_flight > 0:
            self._in_flight -= 1

    @property
    def in_flight(self) -> int:
        return self._in_flight


# Named controllers for major stage boundaries
ENRICHMENT_FLOW = StageFlowController(max_in_flight=4)
INDEXING_FLOW = StageFlowController(max_in_flight=4)
