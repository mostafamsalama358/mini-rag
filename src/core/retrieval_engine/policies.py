"""Execution policies for Retrieval Engine V2."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TimeoutPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    per_retriever_ms: int | None = None
    total_pipeline_ms: int | None = None


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=1, ge=1)
    backoff_ms: int = Field(default=0, ge=0)
    retryable_on: tuple[str, ...] = ()


class CancellationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    cancel_on_budget_exceeded: bool = True
    cancel_on_timeout: bool = True


class PartialResultPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    allow_partial: bool = True
    min_candidates_required: int = Field(default=0, ge=0)


class ExecutionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeout: TimeoutPolicy = Field(default_factory=TimeoutPolicy)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    cancellation: CancellationPolicy = Field(default_factory=CancellationPolicy)
    partial_result: PartialResultPolicy = Field(default_factory=PartialResultPolicy)
