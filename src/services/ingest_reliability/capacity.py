"""Capacity claim hold/release (contracts/admission-capacity.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from services.ingest_reliability.models import WorkloadClass


class ClaimState(str, Enum):
    HELD = "held"
    RELEASED = "released"


@dataclass
class CapacityClaim:
    claim_id: str
    job_id: str
    workload_class: WorkloadClass
    reserved_units: int
    state: ClaimState = ClaimState.HELD
    released_at: Optional[str] = None


@dataclass
class CapacityLedger:
    """In-process ledger for admission accounting (DB persistence is separate)."""

    claims: dict[str, CapacityClaim] = field(default_factory=dict)
    max_concurrent: int = 32
    interactive_reserved: int = 8

    def held_units(self, workload_class: Optional[WorkloadClass] = None) -> int:
        total = 0
        for claim in self.claims.values():
            if claim.state != ClaimState.HELD:
                continue
            if workload_class is not None and claim.workload_class != workload_class:
                continue
            total += claim.reserved_units
        return total

    def interactive_held(self) -> int:
        return sum(
            c.reserved_units
            for c in self.claims.values()
            if c.state == ClaimState.HELD
            and c.workload_class in (WorkloadClass.SMALL, WorkloadClass.LARGE)
        )

    def background_held(self) -> int:
        return sum(
            c.reserved_units
            for c in self.claims.values()
            if c.state == ClaimState.HELD
            and c.workload_class
            in (WorkloadClass.MAINTENANCE, WorkloadClass.MIGRATION)
        )

    def can_accept(
        self,
        workload_class: WorkloadClass,
        *,
        units: int = 1,
    ) -> bool:
        if self.held_units() + units > self.max_concurrent:
            return False
        # Service protection: background cannot consume interactive reserved slots.
        if workload_class in (WorkloadClass.MAINTENANCE, WorkloadClass.MIGRATION):
            interactive_headroom = max(
                0, self.max_concurrent - self.interactive_reserved
            )
            if self.background_held() + units > interactive_headroom:
                return False
        return True

    def hold(
        self,
        *,
        job_id: str,
        workload_class: WorkloadClass,
        units: int = 1,
    ) -> CapacityClaim:
        if not self.can_accept(workload_class, units=units):
            raise RuntimeError("capacity_exhausted")
        claim = CapacityClaim(
            claim_id=str(uuid4()),
            job_id=job_id,
            workload_class=workload_class,
            reserved_units=units,
            state=ClaimState.HELD,
        )
        self.claims[claim.claim_id] = claim
        return claim

    def release(self, claim_id: str) -> CapacityClaim:
        claim = self.claims[claim_id]
        if claim.state == ClaimState.RELEASED:
            return claim
        claim.state = ClaimState.RELEASED
        claim.released_at = datetime.now(timezone.utc).isoformat()
        return claim

    def release_for_job(self, job_id: str) -> int:
        released = 0
        for claim in list(self.claims.values()):
            if claim.job_id == job_id and claim.state == ClaimState.HELD:
                self.release(claim.claim_id)
                released += 1
        return released
