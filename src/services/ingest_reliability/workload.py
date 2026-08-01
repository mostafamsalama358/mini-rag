"""Workload class budgets for memory-bounded ingest (US1)."""

from __future__ import annotations

from dataclasses import dataclass

from helpers.config import Settings
from services.ingest_reliability.job_service import classify_workload
from services.ingest_reliability.models import WorkloadClass


@dataclass(frozen=True)
class WorkloadBudget:
    workload_class: WorkloadClass
    max_in_memory_bytes: int
    max_batch_elements: int
    parse_timeout_seconds: int
    job_timeout_seconds: int


def resolve_workload_class(size_bytes: int, settings: Settings) -> WorkloadClass:
    return classify_workload(size_bytes, settings.INGEST_LARGE_DOCUMENT_BYTES)


def budget_for(workload_class: WorkloadClass, settings: Settings) -> WorkloadBudget:
    """Return configured budgets. Large docs get tighter in-memory ceilings."""
    if workload_class == WorkloadClass.LARGE:
        return WorkloadBudget(
            workload_class=workload_class,
            max_in_memory_bytes=min(
                settings.INGEST_LARGE_DOCUMENT_BYTES,
                8 * 1024 * 1024,
            ),
            max_batch_elements=250,
            parse_timeout_seconds=settings.INGEST_PARSE_TIMEOUT_SECONDS,
            job_timeout_seconds=settings.INGEST_JOB_TIMEOUT_SECONDS,
        )
    if workload_class in (WorkloadClass.MAINTENANCE, WorkloadClass.MIGRATION):
        return WorkloadBudget(
            workload_class=workload_class,
            max_in_memory_bytes=4 * 1024 * 1024,
            max_batch_elements=100,
            parse_timeout_seconds=settings.INGEST_PARSE_TIMEOUT_SECONDS,
            job_timeout_seconds=settings.INGEST_JOB_TIMEOUT_SECONDS,
        )
    return WorkloadBudget(
        workload_class=workload_class,
        max_in_memory_bytes=16 * 1024 * 1024,
        max_batch_elements=1000,
        parse_timeout_seconds=settings.INGEST_PARSE_TIMEOUT_SECONDS,
        job_timeout_seconds=settings.INGEST_JOB_TIMEOUT_SECONDS,
    )
