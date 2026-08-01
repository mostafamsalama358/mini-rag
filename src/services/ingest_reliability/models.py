"""Domain enums and lightweight models for ingest reliability (spec 017)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LifecycleState(str, Enum):
    ACCEPTED = "Accepted"
    VALIDATING = "Validating"
    PARSING = "Parsing"
    DEGRADED_PARSING = "Degraded Parsing"
    CHUNK_PREPARATION = "Chunk Preparation"
    ENRICHMENT = "Enrichment"
    INDEXING = "Indexing"
    PUBLISHING = "Publishing"
    COMPLETED = "Completed"
    COMPLETED_WITH_WARNINGS = "Completed With Warnings"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    TIMED_OUT = "Timed Out"


class ParseOutcomeClass(str, Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"


class FailureOwnership(str, Enum):
    USER_INPUT = "user_input"
    DOCUMENT_QUALITY = "document_quality"
    EXTERNAL_DEPENDENCY = "external_dependency"
    PLATFORM = "platform"
    OPERATOR_ACTION = "operator_action"


class WorkloadClass(str, Enum):
    SMALL = "small"
    LARGE = "large"
    MAINTENANCE = "maintenance"
    MIGRATION = "migration"


class ProgressKind(str, Enum):
    PROGRESSING = "progressing"
    WAITING = "waiting"
    STALLED = "stalled"


class OperationalMode(str, Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    RECOVERY = "recovery"
    ADMISSION_RESTRICTED = "admission_restricted"


class ComponentHealthState(str, Enum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    UNAVAILABLE = "Unavailable"


class AdmissionOutcome(str, Enum):
    ACCEPT = "accept"
    DELAY = "delay"
    REJECT = "reject"


class JobProgress(BaseModel):
    stage: str = ""
    coarse_percent: Optional[float] = None
    kind: ProgressKind = ProgressKind.PROGRESSING
    detail: Optional[str] = None


class IngestJobCreate(BaseModel):
    project_id: int
    logical_document_id: str
    logical_document_version: str
    workload_class: WorkloadClass = WorkloadClass.SMALL
    correlation_id: Optional[str] = None
    configuration_version: str = "1.0.0"
    operational_mode_at_admit: OperationalMode = OperationalMode.NORMAL
    celery_task_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
