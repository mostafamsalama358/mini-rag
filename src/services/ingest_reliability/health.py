"""Component health registry + simple circuit gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from services.ingest_reliability.models import ComponentHealthState


@dataclass
class CircuitState:
    failures: int = 0
    open_until: datetime | None = None
    threshold: int = 5
    cool_down_seconds: int = 60

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            from datetime import timedelta

            self.open_until = datetime.now(timezone.utc) + timedelta(
                seconds=self.cool_down_seconds
            )

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = None

    def is_open(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.open_until is None:
            return False
        if now >= self.open_until:
            self.open_until = None
            self.failures = 0
            return False
        return True


@dataclass
class HealthRegistry:
    states: dict[str, ComponentHealthState] = field(default_factory=dict)
    circuits: dict[str, CircuitState] = field(default_factory=dict)

    def set_health(self, component: str, state: ComponentHealthState) -> None:
        self.states[component] = state

    def get_health(self, component: str) -> ComponentHealthState:
        return self.states.get(component, ComponentHealthState.HEALTHY)

    def circuit(self, component: str) -> CircuitState:
        if component not in self.circuits:
            self.circuits[component] = CircuitState()
        return self.circuits[component]

    def allow(self, component: str) -> bool:
        if self.get_health(component) == ComponentHealthState.UNAVAILABLE:
            return False
        return not self.circuit(component).is_open()


DEFAULT_HEALTH = HealthRegistry()
for _name in ("parser", "ocr", "embedding", "storage", "database", "llm"):
    DEFAULT_HEALTH.set_health(_name, ComponentHealthState.HEALTHY)
